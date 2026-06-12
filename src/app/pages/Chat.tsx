import { useState } from "react";
import { MessageSquare, Plus, Menu } from "lucide-react";
import { Button } from "../components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "../components/ui/sheet";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { NewChatModal } from "../components/chat/NewChatModal";
import { MessageList } from "../components/chat/MessageList";
import { ChatInput } from "../components/chat/ChatInput";
import { KnowledgeGraphViewer } from "../components/chat/KnowledgeGraphViewer";
import { useChatMessages, useChatSessions } from "../../hooks/useChat";
import type { KnowledgeGraphContext } from "../../types/chat";

export default function Chat() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isNewChatModalOpen, setIsNewChatModalOpen] = useState(false);
  const [kgViewerData, setKgViewerData] = useState<KnowledgeGraphContext | null>(null);

  const { data: sessions } = useChatSessions();
  const activeSession = sessions?.find(s => s.id === activeSessionId);

  const { data: messages, sendMessage } = useChatMessages(activeSessionId);

  const handleSendMessage = (content: string, useWebSearch: boolean) => {
    if (!activeSessionId) return;
    sendMessage.mutate({
      sessionId: activeSessionId,
      userMessage: content,
      searchWeb: useWebSearch,
    });
  };

  return (
    <div className="-m-4 sm:-m-6 lg:-m-8 h-[calc(100dvh-4rem)] bg-background">
      <div className="h-full grid grid-cols-1 md:grid-cols-[320px_minmax(0,1fr)]">
        {/* Desktop sidebar */}
        <div className="hidden md:flex h-full border-r bg-muted/30">
          <ChatSidebar
            activeSessionId={activeSessionId}
            onSelectSession={setActiveSessionId}
            onNewChat={() => setIsNewChatModalOpen(true)}
          />
        </div>

        {/* Main pane */}
        <div className="flex flex-col min-h-0">
          {/* Header */}
          <div className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex items-center gap-3 px-4 sm:px-6 py-3">
              {/* Mobile history */}
              <Sheet>
                <SheetTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="md:hidden"
                    title="Chat History"
                  >
                    <Menu className="w-5 h-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="p-0 w-80 border-r-0 shadow-2xl">
                  <ChatSidebar
                    activeSessionId={activeSessionId}
                    onSelectSession={setActiveSessionId}
                    onNewChat={() => setIsNewChatModalOpen(true)}
                  />
                </SheetContent>
              </Sheet>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 min-w-0">
                  <MessageSquare className="w-4 h-4 text-muted-foreground shrink-0" />
                  <h1 className="text-sm font-medium tracking-tight truncate">
                    {activeSession?.title || "AI Tutor"}
                  </h1>
                </div>
                <p className="text-xs text-muted-foreground truncate">
                  {activeSession ? "Ask anything. Use your documents as context." : "Pick a chat session or start a new one."}
                </p>
              </div>

              <Button
                onClick={() => setIsNewChatModalOpen(true)}
                size="sm"
                className="rounded-full shadow-sm hover:shadow transition-all duration-200"
              >
                <Plus className="w-4 h-4 mr-2" />
                New chat
              </Button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-h-0 bg-muted/20">
            {activeSession ? (
              <div className="h-full flex flex-col min-h-0">
                <MessageList
                  messages={messages || []}
                  isSending={sendMessage.isPending}
                  onOpenGraph={setKgViewerData}
                />
                <div className="border-t bg-background">
                  <ChatInput
                    onSendMessage={handleSendMessage}
                    isSending={sendMessage.isPending}
                    disabled={!activeSessionId}
                  />
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center px-6">
                <div className="max-w-md w-full">
                  <div className="rounded-2xl border bg-background shadow-sm p-6 sm:p-8">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                        <MessageSquare className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold tracking-tight">Start a conversation</h3>
                        <p className="text-sm text-muted-foreground">
                          Choose a session from history, or create a new chat.
                        </p>
                      </div>
                    </div>

                    <div className="mt-6 flex flex-col sm:flex-row gap-3">
                      <Button
                        onClick={() => setIsNewChatModalOpen(true)}
                        className="rounded-full transition-all duration-200"
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        New chat
                      </Button>
                      <div className="text-xs text-muted-foreground leading-relaxed sm:pt-2">
                        Tip: On mobile, tap the menu to open your chat history.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      <NewChatModal 
        open={isNewChatModalOpen} 
        onOpenChange={setIsNewChatModalOpen}
        onChatCreated={(id) => setActiveSessionId(id)}
      />

      {kgViewerData && (
        <KnowledgeGraphViewer
          open={!!kgViewerData}
          onOpenChange={(open) => !open && setKgViewerData(null)}
          kgContext={kgViewerData}
        />
      )}
    </div>
  );
}
