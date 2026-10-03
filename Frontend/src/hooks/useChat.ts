import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  createChatSession,
  getChatSessions,
  updateChatSessionTitle,
  deleteChatSession,
  getChatMessages,
  sendChatMessage,
  searchWebMessage,
  transcribeAudio,
  generateTTS,
} from "../services/chatService";
import type { ChatSessionResponse, ChatMessageResponse, UserMessageRequest, WebSearchResponse, AIMessageResponse } from "../types/chat";
import type { LanguageCode } from "../types/language";
import { toast } from "sonner";

export const CHAT_SESSIONS_KEY = ["chatSessions"];
export const CHAT_MESSAGES_KEY = (sessionId: string | null) => ["chatMessages", sessionId];

export function useChatSessions() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: CHAT_SESSIONS_KEY,
    queryFn: getChatSessions,
  });

  const createSession = useMutation({
    mutationFn: createChatSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_KEY });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create chat session");
    },
  });

  const renameSession = useMutation({
    mutationFn: updateChatSessionTitle,
    onSuccess: (_, variables) => {
      // Optimistic update
      queryClient.setQueryData<ChatSessionResponse[]>(CHAT_SESSIONS_KEY, (old) => {
        if (!old) return old;
        return old.map(s => s.id === variables.sessionId ? { ...s, title: variables.title } : s);
      });
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_KEY });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to rename session");
    },
  });

  const deleteSession = useMutation({
    mutationFn: deleteChatSession,
    onSuccess: (_, sessionId) => {
      queryClient.setQueryData<ChatSessionResponse[]>(CHAT_SESSIONS_KEY, (old) => {
        if (!old) return old;
        return old.filter(s => s.id !== sessionId);
      });
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_KEY });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to delete session");
    },
  });

  return {
    ...query,
    createSession,
    renameSession,
    deleteSession,
  };
}

export function useChatMessages(sessionId: string | null) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: CHAT_MESSAGES_KEY(sessionId),
    queryFn: () => getChatMessages(sessionId!),
    enabled: !!sessionId,
    // Polling is not strictly needed if we update cache optimistically, but we can refetch on mount
  });

  const sendMessage = useMutation({
    mutationFn: (payload: UserMessageRequest): Promise<WebSearchResponse | AIMessageResponse> => {
      if (payload.searchWeb) {
        return searchWebMessage(payload);
      } else {
        return sendChatMessage(payload);
      }
    },
    onMutate: async (newMsgPayload) => {
      // Optimistic user message update
      if (!sessionId) return;
      await queryClient.cancelQueries({ queryKey: CHAT_MESSAGES_KEY(sessionId) });
      const previousMessages = queryClient.getQueryData<ChatMessageResponse[]>(CHAT_MESSAGES_KEY(sessionId));
      
      const optimisticMessage: ChatMessageResponse = {
        id: `temp-${Date.now()}`,
        sessionId: newMsgPayload.sessionId,
        role: "User",
        content: newMsgPayload.userMessage,
        createdAt: new Date().toISOString(),
      };

      queryClient.setQueryData<ChatMessageResponse[]>(CHAT_MESSAGES_KEY(sessionId), (old) => {
        return old ? [...old, optimisticMessage] : [optimisticMessage];
      });

      return { previousMessages };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAT_MESSAGES_KEY(sessionId) });
    },
    onError: (err: any, _, context) => {
      if (context?.previousMessages && sessionId) {
        queryClient.setQueryData(CHAT_MESSAGES_KEY(sessionId), context.previousMessages);
      }
      toast.error(err.message || "Failed to send message");
    },
  });

  return {
    ...query,
    sendMessage,
  };
}

export function useAudioFeatures() {
  const sttMutation = useMutation({
    mutationFn: ({ audioFile, language }: { audioFile: File; language: string }) => transcribeAudio(audioFile, language),
    onError: (err: any) => {
      toast.error(err.message || "Speech-to-Text failed");
    },
  });

  const ttsMutation = useMutation({
    mutationFn: ({ messageId, language }: { messageId: string; language: LanguageCode }) =>
      generateTTS(messageId, language),
    onError: () => {
      toast.error("Voice output could not be generated. The text response is unchanged.");
    },
  });

  return {
    sttMutation,
    ttsMutation,
  };
}
