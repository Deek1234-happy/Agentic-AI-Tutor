import { useEffect, useRef } from "react";
import { MessageSquare } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import type { ChatMessageResponse } from "../../../types/chat";

interface MessageListProps {
  messages: ChatMessageResponse[];
  isSending: boolean;
  onOpenGraph: (kgContext: any) => void;
}

export function MessageList({ messages, isSending, onOpenGraph }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  if (messages.length === 0 && !isSending) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <MessageSquare className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
        <h3 className="text-lg font-medium text-foreground mb-2">How can I help you today?</h3>
        <p className="text-sm text-muted-foreground max-w-md">
          Start the conversation! Ask anything about your selected documents, or use the Web Search toggle to explore the internet.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6">
      <div className="max-w-4xl mx-auto w-full space-y-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} onOpenGraph={onOpenGraph} />
        ))}
        
        {isSending && (
          <div className="flex justify-start mb-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div
              className="bg-white border shadow-sm rounded-2xl px-5 py-4 flex h-12 min-w-20 items-center justify-center gap-1.5"
              role="status"
              aria-label="AI tutor is typing"
            >
              <span className="sr-only">AI tutor is typing</span>
              <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:0ms]" />
              <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:150ms]" />
              <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}
        
        <div ref={bottomRef} className="h-px w-full" />
      </div>
    </div>
  );
}
