"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signup } from "@/lib/api/auth";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEye, faEyeSlash} from "@fortawesome/free-solid-svg-icons";

export default function SignupForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function validateEmail(email: string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
      email
    );
  }
  async function handleSubmit( e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setSuccess("");
    const trimmedName = name.trim();
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedName) {
      setError("Please enter your full name.");
      return;
    }
    if (!trimmedEmail) {
      setError("Please enter your email.");
      return;
    }
    if (!validateEmail(trimmedEmail)) {
      setError("Please enter a valid email.");
      return;
    }
    if ([...password].length < 12 || !/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password) || !/[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]/.test(password)) {
      setError("Use at least 12 characters with lowercase, uppercase, a digit, and a symbol.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    try {
      await signup({
        name: trimmedName,
        email: trimmedEmail,
        password,
      });

      setSuccess("Account created successfully! Redirecting to Login...");
      window.setTimeout(() => {
        router.replace("/login");
      }, 1500);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Signup failed."
      );
    }
  }
    return (
    <div className="auth-form">
      <div className="auth-form-heading">
        <h1 className="text-3xl font-bold" style={{ color: "var(--foreground)", }}>
          Create your account
        </h1>
        <p className="text-muted mt-2">
          Make space for your next chapter.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Name */}
        <div>
          <label className="mb-2 block text-sm font-medium" style={{ color: "var(--foreground)" }}>
            Full Name
          </label>
          <input aria-label="Full name" autoComplete="name" type="text" value={name} placeholder="Enter your full name" onChange={(e) => setName(e.target.value)} className="input-theme w-full rounded-xl px-4 py-3"/>
        </div>
        {/* Email */}
        <div>
          <label className="mb-2 block text-sm font-medium" style={{ color: "var(--foreground)" }}>
            Email
          </label>
          <input aria-label="Email" autoComplete="email" type="email" value={email} placeholder="Enter your email" onChange={(e) => setEmail(e.target.value)} className="input-theme w-full rounded-xl px-4 py-3"/>
        </div>
        {/* Password */}
        <div>
          <label className="mb-2 block text-sm font-medium" style={{ color: "var(--foreground)" }}>
            Password
          </label>
          <div className="relative">
            <input aria-label="Password" autoComplete="new-password" type={ showPassword ? "text" : "password"} value={password} placeholder="12+ characters, upper/lowercase, number and symbol" onChange={(e) => setPassword( e.target.value) } className="input-theme w-full rounded-xl px-4 py-3 pr-12"/>
            <button aria-label={showPassword ? "Hide password" : "Show password"} type="button" onClick={() => setShowPassword( (previous) => !previous)} className=" absolute right-4 top-1/2 -translate-y-1/2 text-muted">
              <FontAwesomeIcon icon={ showPassword ? faEyeSlash : faEye}/>
            </button>
          </div>
        </div>
        {/* Confirm Password */}
        <div>
          <label className="mb-2 block text-sm font-medium" style={{ color: "var(--foreground)" }}>
            Confirm Password
          </label>
          <div className="relative">
            <input aria-label="Confirm password" autoComplete="new-password" type={showConfirmPassword ? "text" : "password"} value={confirmPassword} placeholder="Confirm your password" onChange={(e) => setConfirmPassword(e.target.value)} className="input-theme w-full rounded-xl px-4 py-3 pr-12"/>
            <button aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"} type="button" onClick={() => setShowConfirmPassword((previous) => !previous)} className="absolute right-4 top-1/2 -translate-y-1/2 text-muted">
              <FontAwesomeIcon icon={showConfirmPassword ? faEyeSlash : faEye}/>
            </button>
          </div>
        </div>
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-600 dark:border-red-900 dark:bg-red-950/40 dark:text-red-400">
            {error}
          </div>
        )}
        {success && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-600 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-400">
            {success}
          </div>
        )}
        <button type="submit" className="gradient-primary w-full rounded-xl py-3 font-semibold text-white transition hover:opacity-90">
          Create Account
        </button>
      </form>
      <div className="mt-8 text-center">
        <p className="text-muted text-sm">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-blue-600 transition hover:underline">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
