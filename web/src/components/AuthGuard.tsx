"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { fetchIdentity } from "@/lib/api";
import type { IdentityResponse } from "@/lib/api";

export interface AuthGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
  loginPath?: string;
  isAuthenticated?: boolean;
  isLoading?: boolean;
  checkAuth?: () => Promise<boolean | IdentityResponse>;
}

export default function AuthGuard({
  children,
  fallback,
  loginPath = "/login",
  isAuthenticated: controlledAuthenticated,
  isLoading: controlledLoading,
  checkAuth,
}: AuthGuardProps) {
  const router = useRouter();
  const [internalAuthenticated, setInternalAuthenticated] = useState<boolean | null>(
    controlledAuthenticated !== undefined ? controlledAuthenticated : null,
  );
  const [internalLoading, setInternalLoading] = useState(
    controlledLoading !== undefined ? controlledLoading : controlledAuthenticated === undefined,
  );

  useEffect(() => {
    if (controlledAuthenticated !== undefined) {
      setInternalAuthenticated(controlledAuthenticated);
      setInternalLoading(controlledLoading ?? false);
      if (!controlledAuthenticated) {
        router.replace(loginPath);
      }
      return;
    }

    let isMounted = true;
    async function verify() {
      try {
        if (checkAuth) {
          const res = await checkAuth();
          if (!isMounted) return;
          const authOk = Boolean(res);
          setInternalAuthenticated(authOk);
          setInternalLoading(false);
          if (!authOk) {
            router.replace(loginPath);
          }
        } else {
          const identity = await fetchIdentity();
          if (!isMounted) return;
          if (identity && identity.user_id) {
            setInternalAuthenticated(true);
            setInternalLoading(false);
          } else {
            setInternalAuthenticated(false);
            setInternalLoading(false);
            router.replace(loginPath);
          }
        }
      } catch {
        if (!isMounted) return;
        setInternalAuthenticated(false);
        setInternalLoading(false);
        router.replace(loginPath);
      }
    }

    verify();

    return () => {
      isMounted = false;
    };
  }, [controlledAuthenticated, controlledLoading, checkAuth, loginPath, router]);

  const loading = controlledLoading ?? internalLoading;
  const authed = controlledAuthenticated ?? internalAuthenticated;

  if (loading) {
    return (
      fallback ?? (
        <div
          role="status"
          aria-label="Loading authentication..."
          className="p-8 text-center text-sm font-mono text-[#6A6355]"
        >
          Loading…
        </div>
      )
    );
  }

  if (!authed) {
    return (
      fallback ?? (
        <div
          role="alert"
          className="p-8 text-center text-sm font-mono text-[#B0431F]"
        >
          Redirecting to login…
        </div>
      )
    );
  }

  return <>{children}</>;
}
