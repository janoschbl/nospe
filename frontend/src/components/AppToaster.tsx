import { Toaster } from "react-hot-toast";

/** Floating Toasts — themed to match Nospe CSS variables. */
export default function AppToaster() {
  return (
    <Toaster
      position="top-center"
      containerClassName="!top-3"
      toastOptions={{
        duration: 4500,
        className: "!rounded-lg !border !border-border !bg-card !text-foreground !text-[13px] !shadow-lg !px-3.5 !py-2.5",
        style: {
          maxWidth: "min(420px, calc(100vw - 2rem))",
        },
        success: {
          iconTheme: {
            primary: "var(--success)",
            secondary: "var(--card)",
          },
        },
        error: {
          iconTheme: {
            primary: "var(--destructive)",
            secondary: "var(--card)",
          },
        },
      }}
    />
  );
}
