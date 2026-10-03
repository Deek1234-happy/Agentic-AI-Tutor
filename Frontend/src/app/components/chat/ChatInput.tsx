import { useState, useRef, useEffect } from "react";
import { Send, Mic, Globe, Loader2 } from "lucide-react";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { useAudioFeatures } from "../../../hooks/useChat";
import { getLanguageLocale, SUPPORTED_LANGUAGES, type LanguageCode } from "../../../types/language";
import { toast } from "sonner";

interface SpeechRecognitionResultItem {
  transcript: string;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  [index: number]: SpeechRecognitionResultItem;
}

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResult>;
}

interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: new () => BrowserSpeechRecognition;
  webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
}

interface ChatInputProps {
  onSendMessage: (message: string, useWebSearch: boolean, language: LanguageCode) => void;
  isSending: boolean;
  disabled: boolean;
  language: LanguageCode;
  onLanguageChange: (language: LanguageCode) => void;
}

export function ChatInput({ onSendMessage, isSending, disabled, language, onLanguageChange }: ChatInputProps) {
  const [inputMessage, setInputMessage] = useState("");
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const { sttMutation } = useAudioFeatures();
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const speechRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const finalTranscriptRef = useRef("");
  const serverFallbackRequestedRef = useRef(false);
  const [interimTranscript, setInterimTranscript] = useState("");

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputMessage]);

  const handleSend = () => {
    if (!inputMessage.trim() || isSending || disabled) return;
    onSendMessage(inputMessage.trim(), webSearchEnabled, language);
    setInputMessage("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startServerRecording = async () => {
    let stream: MediaStream | null = null;
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        throw new Error("Audio recording is not supported by this browser.");
      }

      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferredMimeType = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((mimeType) => MediaRecorder.isTypeSupported(mimeType));
      const mediaRecorder = new MediaRecorder(
        stream,
        preferredMimeType ? { mimeType: preferredMimeType } : undefined
      );
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        stream?.getTracks().forEach((track) => track.stop());

        const chunks = audioChunksRef.current;
        if (chunks.length === 0) {
          toast.error("No audio was recorded. Please try again.");
          return;
        }

        const recordedType = (mediaRecorder.mimeType || chunks[0].type || "audio/webm")
          .split(";")[0]
          .toLowerCase();
        const extensionByType: Record<string, string> = {
          "audio/webm": "webm",
          "audio/ogg": "ogg",
          "audio/mp4": "m4a",
          "audio/wav": "wav",
        };
        const extension = extensionByType[recordedType];
        if (!extension) {
          toast.error(`The recorded audio format (${recordedType}) is not supported.`);
          return;
        }

        const audioBlob = new Blob(chunks, { type: recordedType });
        const file = new File([audioBlob], `recording.${extension}`, { type: recordedType });

        sttMutation.mutate({ audioFile: file, language }, {
          onSuccess: (res) => {
            const transcript = res.text?.trim();
            if (!transcript) {
              toast.error("No speech was detected. Please try again.");
              return;
            }
            setInputMessage((previous) => previous ? `${previous} ${transcript}` : transcript);
          },
        });
      };

      mediaRecorder.onerror = () => {
        stream?.getTracks().forEach((track) => track.stop());
        setIsRecording(false);
        toast.error("Recording failed. Check microphone access and try again.");
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Microphone access denied:", error);
      stream?.getTracks().forEach((track) => track.stop());
      setIsRecording(false);
      toast.error(error instanceof Error ? error.message : "Could not start microphone recording.");
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      if (speechRecognitionRef.current) {
        speechRecognitionRef.current.stop();
      } else {
        mediaRecorderRef.current?.stop();
      }
      return;
    }

    const speechWindow = window as SpeechRecognitionWindow;
    const SpeechRecognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      speechRecognitionRef.current = recognition;
      finalTranscriptRef.current = "";
      setInterimTranscript("");
      recognition.lang = getLanguageLocale(language);
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.onresult = (event) => {
        let interim = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = result[0]?.transcript ?? "";
          if (result.isFinal) {
            finalTranscriptRef.current += `${transcript} `;
          } else {
            interim += transcript;
          }
        }
        setInterimTranscript(interim.trim());
      };
      recognition.onerror = (event) => {
        speechRecognitionRef.current = null;
        setIsRecording(false);
        setInterimTranscript("");
        if (event.error === "language-not-supported") {
          serverFallbackRequestedRef.current = true;
          toast.info("Live recognition does not support this language here. Using server transcription.");
          void startServerRecording();
          return;
        }
        if (event.error !== "aborted" && event.error !== "no-speech") {
          toast.error(event.error === "not-allowed"
            ? "Microphone access was blocked. Allow microphone access and try again."
            : `Live speech recognition failed: ${event.error}.`);
        }
      };
      recognition.onend = () => {
        if (serverFallbackRequestedRef.current) {
          serverFallbackRequestedRef.current = false;
          return;
        }
        const transcript = finalTranscriptRef.current.trim();
        speechRecognitionRef.current = null;
        setIsRecording(false);
        setInterimTranscript("");
        if (transcript) {
          setInputMessage((previous) => previous ? `${previous} ${transcript}` : transcript);
        } else if (finalTranscriptRef.current.length === 0) {
          toast.error("No speech was detected. Please try again.");
        }
      };

      try {
        recognition.start();
        setIsRecording(true);
      } catch (error) {
        speechRecognitionRef.current = null;
        if (language !== "en" && error instanceof DOMException && error.name === "NotSupportedError") {
          toast.info("Live recognition does not support this language here. Using server transcription.");
          await startServerRecording();
          return;
        }
        toast.error(error instanceof Error ? error.message : "Could not start live speech recognition.");
      }
      return;
    }

    await startServerRecording();
  };

  return (
    <div className="border-t p-4 bg-muted/30">
      <div className="max-w-4xl mx-auto w-full flex flex-col gap-2">
        <div className="flex items-end gap-2 bg-background border rounded-xl p-2 focus-within:ring-1 focus-within:ring-primary shadow-sm">
          <Button
            variant={isRecording ? "destructive" : "ghost"}
            size="icon"
            onClick={toggleRecording}
            disabled={disabled || sttMutation.isPending}
            className={`shrink-0 rounded-full ${isRecording ? "animate-pulse" : ""}`}
            title={isRecording ? "Stop recording" : "Dictate message"}
            type="button"
          >
            {sttMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Mic className="w-5 h-5" />}
          </Button>
          
          <textarea
            ref={textareaRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isSending}
            placeholder="Ask a question about your documents..."
            className="flex-1 max-h-[200px] min-h-[40px] resize-none bg-transparent py-2 px-1 focus:outline-none text-base disabled:opacity-50"
            rows={1}
          />
          
          <Button
            onClick={handleSend}
            disabled={!inputMessage.trim() || disabled || isSending}
            size="icon"
            className="shrink-0 rounded-full h-10 w-10"
          >
            {isSending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-4 h-4 ml-0.5" />}
          </Button>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 px-2">
          <div className="flex items-center gap-2">
            {isRecording && !speechRecognitionRef.current && (
              <p className="text-sm text-destructive font-medium flex items-center gap-2">
                <span className="w-2 h-2 bg-destructive rounded-full animate-pulse" />
                Recording...
              </p>
            )}
            {isRecording && speechRecognitionRef.current && (
              <p className="text-sm text-destructive font-medium" role="status">
                Listening... {interimTranscript}
              </p>
            )}
            {sttMutation.isPending && (
              <p className="text-sm text-muted-foreground" role="status">Transcribing audio...</p>
            )}
          </div>
          
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Label htmlFor="chat-language" className="text-xs text-muted-foreground font-medium">
                Language
              </Label>
              <Select
                value={language}
                onValueChange={(value) => onLanguageChange(value as LanguageCode)}
                disabled={disabled || isRecording || sttMutation.isPending}
              >
                <SelectTrigger id="chat-language" className="h-8 w-[132px] text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SUPPORTED_LANGUAGES.map((item) => (
                    <SelectItem key={item.code} value={item.code}>{item.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Label htmlFor="web-search" className="text-xs text-muted-foreground cursor-pointer flex items-center gap-1.5 font-medium">
              <Globe className={`w-3.5 h-3.5 ${webSearchEnabled ? "text-primary" : ""}`} />
              Web Search
            </Label>
            <Switch
              id="web-search"
              checked={webSearchEnabled}
              onCheckedChange={setWebSearchEnabled}
              disabled={disabled}
              className="scale-75 origin-right"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
