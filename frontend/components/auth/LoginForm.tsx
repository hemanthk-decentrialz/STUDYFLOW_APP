"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { login as loginRequest } from "@/lib/api/auth";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEye, faEyeSlash } from "@fortawesome/free-solid-svg-icons";

export default function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail) {
      setError(
        "Please enter your email."
      );
      return;
    }
    if (!password.trim()) {
      setError(
        "Please enter your password."
      );
      return;
    }
    try {
      const user = await loginRequest({
        email: trimmedEmail,
        password,
      });

      await login(user);
      router.replace("/");
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Login failed."
      );
    }
  }
  return (
    <div className="auth-form">
      <div className="auth-form-heading">
        <h1 className="text-3xl font-bold" style={{ color: "var(--foreground)", }}>
          Welcome back.
        </h1>
        <p className="text-muted mt-2">
          Pick up where you left off.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="mb-2 block text-sm font-medium" style={{ color: "var(--foreground)" }}>
            Email
          </label>
          <input aria-label="Email" autoComplete="email" type="email" placeholder="Enter your email" value={email}
            onChange={(e) =>
              setEmail(
                e.target.value
              )
            } className="input-theme w-full rounded-xl px-4 py-3"
          />
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium" style={{ color: "var(--foreground)" }}>
            Password
          </label>
          <div className="relative">
            <input aria-label="Password" autoComplete="current-password" type={showPassword ? "text" : "password"} placeholder="Enter password" value={password}
              onChange={(e) =>
                setPassword(
                  e.target.value
                )
              } className="input-theme w-full rounded-xl px-4 py-3 pr-12"
            />
            <button aria-label={showPassword ? "Hide password" : "Show password"} type="button"
              onClick={() =>
                setShowPassword(
                  (previous) =>
                    !previous
                )
              } className="absolute right-4 top-1/2 -translate-y-1/2 text-muted"
            >
              <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} />
            </button>
          </div>
        </div>
        {error && (
          <p className="text-sm font-medium status-error">
            {error}
          </p>
        )}
        <button type="submit" className="gradient-primary w-full rounded-xl py-3 font-semibold text-(--on-primary) transition-opacity hover:opacity-90">
          Login
        </button>
      </form>
      <div className="mt-8 text-center">
        <p className="text-muted text-sm">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="font-semibold text-(--primary)">
            Sign Up
          </Link>
        </p>
      </div>
    </div>
  );
}
