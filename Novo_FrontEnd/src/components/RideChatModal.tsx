import React, { useState, useEffect, useRef } from "react";
import {
  X,
  Send,
  Image as ImageIcon,
  Search,
  Phone,
  ShieldCheck,
  Check,
  CheckCheck,
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

    // Removed setTimeout mockup for motoboy response
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-zinc-900/40 backdrop-blur-sm z-[1000] flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-xl w-full max-w-md h-[600px] max-h-[90vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="p-4 border-b border-zinc-100 flex items-center justify-between bg-white z-10 shrink-0">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-zinc-100 flex items-center justify-center text-lg font-bold text-zinc-700">
                {corrida.motoboy?.nome
                  ? corrida.motoboy.nome.charAt(0).toUpperCase()
                  : "M"}
              </div>
              <div>
                <h3 className="text-sm font-bold text-zinc-900">
                  {corrida.motoboy?.nome || "Motorista"}
                </h3>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span className="text-[11px] font-medium text-emerald-600">
                    Online
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors">
                <Phone className="h-4 w-4" />
              </button>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Messages info banner */}
          <div className="bg-zinc-50 border-b border-zinc-100 px-4 py-2 flex items-center gap-2 shrink-0">
            <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
            <span className="text-[11px] text-zinc-500 font-medium">
              As mensagens são end-to-end e monitoradas para segurança.
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-zinc-50/30">
            <div className="flex flex-col gap-4">
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
                        "max-w-[75%] rounded-2xl px-4 py-2.5",
                        isMe
                          ? "bg-zinc-900 text-white rounded-tr-sm"
                          : "bg-zinc-100 text-zinc-800 rounded-tl-sm border border-zinc-200/50",
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

          {/* Input */}
          <div className="p-4 border-t border-zinc-100 bg-white shrink-0">
            <form onSubmit={handleSend} className="flex gap-2">
              <button
                type="button"
                className="p-2.5 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-all shrink-0"
              >
                <ImageIcon className="w-5 h-5" />
              </button>
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Escreva uma mensagem..."
                className="flex-1 px-4 py-2.5 bg-zinc-100 border border-transparent rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:bg-white focus:border-zinc-200 transition-all placeholder:text-zinc-500"
              />
              <button
                type="submit"
                disabled={!inputText.trim()}
                className="p-2.5 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 disabled:opacity-50 disabled:hover:bg-emerald-500 transition-all shrink-0 shadow-sm"
              >
                <Send className="w-5 h-5 ml-0.5" />
              </button>
            </form>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
