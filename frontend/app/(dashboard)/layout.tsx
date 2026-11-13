"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import DashboardLayout from "@/components/layout/DashboardLayout";
import Button from "@/components/ui/Button";
import FullPageLoader from "@/components/ui/FullPageLoader";
import { useAuth } from "@/context/AuthContext";

export default function Layout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter();
  const { isAuthenticated, isLoading, sessionError, retrySession } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !sessionError) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, sessionError, router]);

  if (sessionError) {
    return <main className="auth-page"><section className="dashboard-card max-w-md p-8" role="alert">
      <h1 className="text-xl font-semibold">Unable to reconnect</h1>
      <p className="text-muted my-4">{sessionError}</p>
      <Button onClick={retrySession}>Try again</Button>
    </section></main>;
  }

  if (isLoading || !isAuthenticated) {
    return <FullPageLoader defer />;
  }

  return (

    <DashboardLayout>

      {children}

    </DashboardLayout>

  );

}
