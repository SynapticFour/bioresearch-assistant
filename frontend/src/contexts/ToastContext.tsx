import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import * as Toast from "@radix-ui/react-toast";
import { cn } from "@/lib/utils";

type ToastVariant = "success" | "error";

interface ToastState {
  open: boolean;
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toast, setToast] = useState<ToastState>({
    open: false,
    message: "",
    variant: "success",
  });

  const showSuccess = useCallback((message: string) => {
    setToast({ open: true, message, variant: "success" });
  }, []);

  const showError = useCallback((message: string) => {
    setToast({ open: true, message, variant: "error" });
  }, []);

  const onOpenChange = useCallback((open: boolean) => {
    if (!open) setToast((t) => ({ ...t, open: false }));
  }, []);

  return (
    <ToastContext.Provider value={{ showSuccess, showError }}>
      <Toast.Provider duration={5000} label="Benachrichtigungen">
        <Toast.Root
          open={toast.open}
          onOpenChange={onOpenChange}
          className={cn(
            "rounded-lg border px-4 py-3 shadow-lg",
            toast.variant === "success" &&
              "border-green-200 bg-green-50 text-green-900",
            toast.variant === "error" &&
              "border-red-200 bg-red-50 text-red-900"
          )}
        >
          <Toast.Title className="font-medium">{toast.message}</Toast.Title>
        </Toast.Root>
        <Toast.Viewport
          className={cn(
            "fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col gap-2 p-4",
            "sm:max-w-[380px]"
          )}
          style={{ listStyle: "none" }}
        />
        {children}
      </Toast.Provider>
    </ToastContext.Provider>
  );
}
