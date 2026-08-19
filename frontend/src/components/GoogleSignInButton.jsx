import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

/**
 * Renders Google's own "Sign in with Google" button (via Google Identity
 * Services, loaded as a <script> tag in index.html) and wires its callback
 * into our AuthContext. If VITE_GOOGLE_CLIENT_ID isn't set at build time,
 * this renders nothing rather than a broken button -- Google sign-in is
 * optional, not a hard requirement for the app to work.
 */
export default function GoogleSignInButton({ onError, note }) {
  const buttonRef = useRef(null);
  const [scriptReady, setScriptReady] = useState(false);
  const { loginWithGoogle } = useAuth();

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    // The GSI script tag has async/defer, so window.google may not exist
    // yet on first render -- poll briefly rather than assuming it's ready.
    let attempts = 0;
    const interval = setInterval(() => {
      attempts += 1;
      if (window.google?.accounts?.id) {
        setScriptReady(true);
        clearInterval(interval);
      } else if (attempts > 40) {
        clearInterval(interval); // ~10s timeout -- give up quietly
      }
    }, 250);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!scriptReady || !buttonRef.current) return;

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        try {
          await loginWithGoogle(response.credential);
          window.location.href = "/dashboard";
        } catch (err) {
          onError?.(
            err.response?.status === 501
              ? "Google sign-in isn't configured on the server yet."
              : "Google sign-in failed. Please try again."
          );
        }
      },
    });

    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "outline",
      size: "large",
      width: 320,
      text: "continue_with",
    });
  }, [scriptReady, loginWithGoogle, onError]);

  if (!GOOGLE_CLIENT_ID) return null;

  return (
    <div className="flex flex-col items-center gap-3 my-2">
      <div className="flex items-center gap-3 w-full">
        <div className="flex-1 h-px bg-console-border" />
        <span className="text-console-muted text-[10px] font-mono uppercase tracking-wide">
          or
        </span>
        <div className="flex-1 h-px bg-console-border" />
      </div>
      <div ref={buttonRef} />
      {note && <p className="text-console-muted text-[10px] font-mono text-center">{note}</p>}
    </div>
  );
}
