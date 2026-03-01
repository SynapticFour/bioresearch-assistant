import * as Toast from "@radix-ui/react-toast";
import { cn } from "@/lib/utils";

interface ToasterProps {
  children: React.ReactNode;
}

export function Toaster({ children }: ToasterProps) {
  return (
    <Toast.Provider duration={5000} label="Benachrichtigungen">
      {children}
      <Toast.Viewport
        className={cn(
          "fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col gap-2 p-4",
          "sm:max-w-[380px]"
        )}
        style={{ listStyle: "none" }}
      />
    </Toast.Provider>
  );
}
