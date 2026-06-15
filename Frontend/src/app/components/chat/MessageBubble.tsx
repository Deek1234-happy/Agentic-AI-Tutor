import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Volume2, ChevronDown, ChevronUp, FileText, ExternalLink, Network, Loader2 } from "lucide-react";
import { Button } from "../ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../ui/collapsible";
import { useAudioFeatures } from "../../../hooks/useChat";
import type { ChatMessageResponse } from "../../../types/chat";
import { toast } from "sonner";
import { useQuery } from "@tanstack/react-query";
import { getDocumentById } from "../../../services/documentService";

interface MessageBubbleProps {
  message: ChatMessageResponse;
  onOpenGraph: (kgContext: any) => void;
}


function CitationDocumentName({ documentId, fallback, hasMetadataName }: { documentId?: string; fallback: string; hasMetadataName: boolean }) {
  const { data } = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocumentById(documentId!),
    enabled: !!documentId && !hasMetadataName,
    staleTime: Infinity,
  });

  return <>{data?.fileName || fallback}</>;
}

export function MessageBubble({ message, onOpenGraph }: MessageBubbleProps) {
  const isUser = message.role?.toLowerCase() === "user" || message.role?.toLowerCase() === "student";
  const kg = message.kgContext || message.kg_context;
  const { ttsMutation } = useAudioFeatures();
  const [citationsOpen, setCitationsOpen] = useState(false);
  const [webSourcesOpen, setWebSourcesOpen] = useState(false);
  const [playingAudio, setPlayingAudio] = useState<HTMLAudioElement | null>(null);

  const handleListen = () => {
    if (playingAudio) {
      playingAudio.pause();
      setPlayingAudio(null);
      return;
    }

    ttsMutation.mutate(message.id, {
      onSuccess: async (res) => {
        try {
          const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5099";
          
          // Fix backend bug where it returns 'http://localhost:5099http://localhost:5099/...'
          const cleanUrl = res.audio_url.replace(/^(https?:\/\/[^\/]+)\1/, "$1");

          const url = cleanUrl.startsWith("http") 
            ? cleanUrl 
            : `${baseUrl}${cleanUrl.startsWith("/") ? "" : "/"}${cleanUrl}`;

          const audio = new Audio(url);
          
          audio.onended = () => {
            setPlayingAudio(null);
          };
          audio.onerror = () => {
            setPlayingAudio(null);
            toast.error("Failed to load audio file.");
          };
          await audio.play();
          setPlayingAudio(audio);
        } catch (error) {
          console.error("Audio playback error:", error);
          toast.error("Failed to load audio file.");
          setPlayingAudio(null);
        }
      }
    });
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6 w-full`}>
      <div className={`${isUser ? "max-w-[85%]" : "max-w-full"} ${isUser ? "" : "space-y-2"}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser ? "bg-primary text-primary-foreground" : "bg-white border shadow-sm text-foreground"
          }`}
        >
          {isUser ? (
            <p className="text-[15px] whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-muted prose-pre:text-muted-foreground">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {!isUser && (
            <div className="flex items-center gap-2 mt-3 pt-2 border-t border-border/50">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs font-medium text-muted-foreground hover:text-primary"
                onClick={handleListen}
                disabled={ttsMutation.isPending}
              >
                {ttsMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Volume2 className={`w-3.5 h-3.5 mr-1.5 ${playingAudio ? "text-primary animate-pulse" : ""}`} />
                )}
                {playingAudio ? "Stop" : "Listen"}
              </Button>

              {kg?.entities && kg.entities.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs font-medium text-muted-foreground hover:text-primary"
                  onClick={() => onOpenGraph(kg)}
                >
                  <Network className="w-3.5 h-3.5 mr-1.5" />
                  View Graph
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.aiCitation && message.aiCitation.length > 0 && (
          <Collapsible open={citationsOpen} onOpenChange={setCitationsOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5 w-auto rounded-full bg-background/50">
                {citationsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {citationsOpen ? "Hide Sources" : `${message.aiCitation.length} Sources`}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2">
              <div className="flex flex-wrap gap-2">
                {message.aiCitation.map((cit, idx) => (
                  <div key={idx} className="flex flex-col gap-1 p-2.5 rounded-lg border bg-card text-card-foreground text-xs min-w-[200px] max-w-[300px]">
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-1.5 font-medium text-primary">
                        <FileText className="w-3 h-3 shrink-0" />
                        <span className="truncate">
                          <CitationDocumentName 
                            documentId={cit.document_id} 
                            fallback={cit.document_name || cit.fileName || cit.file_name || cit.document_id || "Document Reference"}
                            hasMetadataName={!!(cit.document_name || cit.fileName || cit.file_name)}
                          />
                        </span>
                      </div>
                      {(cit.page_start != null && cit.page_end != null) && (
                        <span className="text-[10px] text-muted-foreground ml-4 font-medium">
                          Pages {cit.page_start} - {cit.page_end}
                        </span>
                      )}
                    </div>
                    {(cit.snippet || cit.content) && (
                      <p className="text-muted-foreground line-clamp-3 text-[11px] leading-relaxed italic mt-1 border-l-2 pl-2">
                        "{cit.snippet || cit.content}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Web Sources */}
        {!isUser && message.webSource && message.webSource.length > 0 && (
          <Collapsible open={webSourcesOpen} onOpenChange={setWebSourcesOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5 w-auto rounded-full bg-background/50">
                {webSourcesOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {webSourcesOpen ? "Hide Web Sources" : `${message.webSource.length} Web Sources`}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2">
              <div className="flex flex-wrap gap-2">
                {message.webSource.map((src, idx) => (
                  <a
                    key={idx}
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-col gap-1 p-2.5 rounded-lg border bg-card text-card-foreground hover:border-primary/50 transition-colors text-xs min-w-[200px] max-w-[300px] group"
                  >
                    <div className="flex items-center gap-1.5 font-medium group-hover:text-primary transition-colors">
                      <ExternalLink className="w-3 h-3" />
                      <span className="truncate">{src.title}</span>
                    </div>
                    <p className="text-muted-foreground line-clamp-2 text-[11px] leading-relaxed">
                      {src.snippet}
                    </p>
                  </a>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  );
}
