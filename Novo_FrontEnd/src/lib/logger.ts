const isDevelopment =
  (typeof window !== "undefined" &&
    ["localhost", "127.0.0.1"].includes(window.location.hostname)) ||
  (typeof process !== "undefined" && process.env.NODE_ENV !== "production");

export const logger = {
  info: (...args: any[]) => {
    if (isDevelopment) {
      console.info("[INFO]", ...args);
    }
  },
  warn: (...args: any[]) => {
    if (isDevelopment) {
      console.warn("[WARN]", ...args);
    }
  },
  error: (...args: any[]) => {
    console.error("[ERROR]", ...args);
  },
  debug: (...args: any[]) => {
    if (isDevelopment) {
      console.debug("[DEBUG]", ...args);
    }
  },
};
