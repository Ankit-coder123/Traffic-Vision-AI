import { createContext, useContext, useState, useEffect } from "react";
import { authApi } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("tv_token");
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem("tv_token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const res = await authApi.login(email, password);
    localStorage.setItem("tv_token", res.data.access_token);
    const me = await authApi.me();
    setUser(me.data);
    return me.data;
  };

  const loginWithGoogle = async (credential) => {
    const res = await authApi.googleLogin(credential);
    localStorage.setItem("tv_token", res.data.access_token);
    const me = await authApi.me();
    setUser(me.data);
    return me.data;
  };

  const updateProfile = async (payload) => {
    const res = await authApi.updateProfile(payload);
    setUser(res.data);
    return res.data;
  };

  const signup = async (name, email, password, role = "user") => {
    // Public signup only ever sends 'operator' or 'user' -- 'admin' isn't
    // offered as a choice in the UI (see Signup.jsx).
    await authApi.signup(name, email, password, role);
    return login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("tv_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, updateProfile, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
