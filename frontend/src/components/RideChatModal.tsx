import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  X,
  Send,
  Image as ImageIcon,
  Search,
  Phone,
  ShieldCheck,
  Check,
  CheckCheck,
  MessageSquare,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";

interface RideChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  corrida: any;
}

export function RideChatModal({
  isOpen,
  onClose,
  corrida,
}: RideChatModalProps) {
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && corrida) {
      setMessages([]);
    }
  }, [isOpen, corrida]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  if (!isOpen || !corrida) return null;

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const newMessage = {
      id: Date.now(),
      text: inputText,
      sender: "admin",
      time: new Date().toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      status: "sent",
    };

    setMessages([...messages, newMessage]);
    setInputText("");
  };

  return typeof document !== "undefined"
    ? createPortal(
        <AnimatePresence>
          <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onClose}
              className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
            />

            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 260 }}
              className="fixed top-0 right-0 h-full w-full max-w-md md:max-w-lg bg-white shadow-2xl z-10 flex flex-col pointer-events-auto border-l border-zinc-200"
            >
              {/* Header */}
              <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/80 backdrop-blur-xs shrink-0">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="h-10 w-10 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold shadow-xs">
                      {corrida.motoboy?.nome
                        ? corrida.motoboy.nome.charAt(0).toUpperCase()
                        : "M"}
                    </div>
                    <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-white"></span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-2 py-0.5 rounded-full">
                        Chat da Corrida #{corrida.id}
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-zinc-900 mt-0.5">
                      {corrida.motoboy?.nome || "Motorista"}
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={onClose}
                    className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Security info banner */}
              <div className="bg-zinc-50 border-b border-zinc-100 px-6 py-2 flex items-center gap-2 shrink-0">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="text-[11px] text-zinc-500 font-medium">
                  Comunicação criptografada monitorada para segurança operacional.
                </span>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-zinc-50/30">
                <div className="flex flex-col gap-4">
                  {messages.length === 0 && (
                    <div className="py-12 text-center text-zinc-400 text-xs">
                      <MessageSquare className="h-8 w-8 mx-auto mb-2 text-zinc-300" />
                      Inicie a conversa com o motorista...
                    </div>
                  )}
                  {messages.map((message) => {
                    const isMe = message.sender === "admin";
                    return (
                      <div
                        key={message.id}
                        className={cn(
                          "flex w-full",
                          isMe ? "justify-end" : "justify-start",
                        )}
                      >
                        <div
                          className={cn(
                            "max-w-[75%] rounded-2xl px-4 py-2.5 shadow-xs",
                            isMe
                              ? "bg-zinc-900 text-white rounded-tr-sm"
                              : "bg-white text-zinc-800 rounded-tl-sm border border-zinc-200/80",
                          )}
                        >
                          <p className="text-sm leading-relaxed">{message.text}</p>
                          <div
                            className={cn(
                              "flex items-center gap-1 mt-1 justify-end",
                              isMe ? "text-zinc-400" : "text-zinc-400",
                            )}
                          >
                            <span className="text-[10px] uppercase font-medium tracking-wider">
                              {message.time}
                            </span>
                            {isMe &&
                              (message.status === "read" ? (
                                <CheckCheck className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Check className="w-3 h-3" />
                              ))}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Input Footer */}
              <div className="p-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs shrink-0">
                <form onSubmit={handleSend} className="flex gap-2">
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Escreva uma mensagem para o condutor..."
                    className="flex-1 px-4 py-2.5 bg-white border border-zinc-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all placeholder:text-zinc-400"
                  />
                  <button
                    type="submit"
                    disabled={!inputText.trim()}
                    className="px-4 py-2.5 bg-zinc-900 text-white rounded-xl hover:bg-zinc-800 disabled:opacity-50 transition-all shrink-0 shadow-sm cursor-pointer flex items-center gap-1.5 text-xs font-bold"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            </motion.div>
          </div>
        </AnimatePresence>,
        document.body
      )
    : null;
}
