import { apiRequest } from "@/lib/api/client";
import { SessionUser } from "@/types/auth";

export interface SignupPayload {
  name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export function signup(payload: SignupPayload) {
  return apiRequest<SessionUser>("/api/v1/users", {
    method: "POST",
    body: payload,
  });
}

export function login(payload: LoginPayload) {
  return apiRequest<SessionUser>("/api/v1/sessions", {
    method: "POST",
    body: payload,
  });
}

export function getCurrentUser() {
  return apiRequest<SessionUser>("/api/v1/users/me");
}

export function logout() {
  return apiRequest<void>("/api/v1/sessions/current", {
    method: "DELETE",
  });
}


export function updateProfile(payload: { name: string }) {
  return apiRequest<SessionUser>("/api/v1/users/me", { method: "PATCH", body: payload });
}
