import { useState, useRef, useEffect } from "react";
import { Send, Mic, Globe, Loader2 } from "lucide-react";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Label } from "../ui/label";
import { useAudioFeatures } from "../../../hooks/useChat";

interface ChatInputProps {
  onSendMessage: (message: string, useWebSearch: boolean) => void;
  isSending: boolean;
  disabled: boolean;
}

export function ChatInput({ onSendMessage, isSending, disabled }: ChatInputProps) {
  const [inputMessage, setInputMessage] = useState("");
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const { sttMutation } = useAudioFeatures();
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputMessage]);

  const handleSend = () => {
    if (!inputMessage.trim() || isSending || disabled) return;
    onSendMessage(inputMessage.trim(), webSearchEnabled);
    setInputMessage("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/mp3" });
        // Clean up tracks
        stream.getTracks().forEach((track) => track.stop());
        
        // Ensure File name has extension since STT often relies on it
        const file = new File([audioBlob], "recording.mp3", { type: "audio/mp3" });
        
        sttMutation.mutate(file, {
          onSuccess: (res) => {
            setInputMessage(prev => prev ? `${prev} ${res.text}` : res.text);
          }
        });
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Microphone access denied:", error);
    }
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

        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2">
            {isRecording && (
              <p className="text-sm text-destructive font-medium flex items-center gap-2">
                <span className="w-2 h-2 bg-destructive rounded-full animate-pulse" />
                Recording...
              </p>
            )}
          </div>
          
          <div className="flex items-center gap-2">
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
