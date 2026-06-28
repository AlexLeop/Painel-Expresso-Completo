import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WifiOff, X } from "lucide-react";

export function NetworkToast() {
  const [messages, setMessages] = useState<{ id: number; text: string }[]>([]);

  useEffect(() => {
    const handleNetworkError = (event: Event) => {
      const customEvent = event as CustomEvent<string>;
      const newMsg = { id: Date.now(), text: customEvent.detail };
      setMessages((prev) => [...prev, newMsg]);

      setTimeout(() => {
        setMessages((prev) => prev.filter((m) => m.id !== newMsg.id));
      }, 5000);
    };

    window.addEventListener("nevesgo:network-error", handleNetworkError);
    return () => {
      window.removeEventListener("nevesgo:network-error", handleNetworkError);
    };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2">
      <AnimatePresence>
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
            className="bg-red-600 text-white px-4 py-3 rounded-lg shadow-xl flex items-center gap-3 min-w-[300px]"
          >
            <WifiOff className="w-5 h-5 text-red-200" />
            <span className="text-sm font-medium flex-1">{msg.text}</span>
            <button
              onClick={() => setMessages((prev) => prev.filter((m) => m.id !== msg.id))}
              className="text-red-200 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
