"use client";

import React, { useState, useEffect } from "react";
import { X, Search, GitFork, MessageSquare, Lightbulb, Braces, ArrowRight } from "lucide-react";

const capabilities = [
    {
        icon: Search,
        title: "Code Retrieval (RAG)",
        desc: "Semantic search over your indexed repo with vector embeddings + reranking, returning grounded answers with citations.",
        repoOnly: true,
    },
    {
        icon: MessageSquare,
        title: "Coding Mentor",
        desc: "Explains code, answers architecture questions, reviews logic, and teaches best practices like a senior engineer.",
        repoOnly: false,
    },
    {
        icon: Lightbulb,
        title: "Context Memory",
        desc: "Remembers your conversation so follow-up questions ('refactor it', 'what about that file?') build on previous answers.",
        repoOnly: false,
    },
    {
        icon: GitFork,
        title: "Dependency Graph",
        desc: "Builds and visualizes the import graph so you can see which files depend on what across the codebase.",
        repoOnly: true,
    },
];

export default function WelcomeModal() {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        // Only greet when arriving from the home page (it sets this flag).
        // Internal navigation (e.g. back from Eval) won't, so no repeat popup.
        if (sessionStorage.getItem("codexa_show_welcome") === "1") {
            setVisible(true);
            sessionStorage.removeItem("codexa_show_welcome");
        }
    }, []);

    const dismiss = () => setVisible(false);

    if (!visible) return null;

    const hasRepo = typeof window !== "undefined" && !!localStorage.getItem("current_repo_id");
    const shown = capabilities.filter((c) => hasRepo || !c.repoOnly);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="relative bg-card border border-border rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Glow accent */}
                <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-72 h-48 brand-gradient opacity-20 blur-3xl pointer-events-none" />

                {/* Header */}
                <div className="relative flex items-center justify-between px-8 py-6 border-b border-border">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl brand-gradient accent-glow flex items-center justify-center">
                            <Braces className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold tracking-tight brand-text">
                                Codexa
                            </h2>
                            <p className="text-[11px] text-muted mt-0.5">
                                {hasRepo
                                    ? "Your repository is indexed and ready to explore."
                                    : "General coding workspace — ask anything about programming."}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={dismiss}
                        className="p-1.5 text-muted hover:text-foreground transition-colors rounded-lg hover:bg-white/5"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Capabilities */}
                <div className="relative px-8 py-6 space-y-4">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted/60">
                        What Codexa can do
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {shown.map((cap) => (
                            <div
                                key={cap.title}
                                className="group flex gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:border-accent/40 hover:bg-white/[0.05] transition-all"
                            >
                                <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0 group-hover:bg-accent/20 transition-colors">
                                    <cap.icon className="w-4 h-4 text-accent" />
                                </div>
                                <div>
                                    <div className="text-[12px] font-semibold text-foreground/90">{cap.title}</div>
                                    <div className="text-[11px] text-muted leading-relaxed mt-0.5">{cap.desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <div className="relative px-8 py-4 border-t border-border flex items-center justify-between">
                    <p className="text-[10px] text-muted/50 uppercase tracking-widest">
                        Retrieval · Memory · Mentor
                    </p>
                    <button
                        onClick={dismiss}
                        className="group px-6 py-2 bg-accent text-white rounded-lg text-[12px] font-bold hover:opacity-90 transition-opacity accent-glow flex items-center gap-1.5"
                    >
                        Let&apos;s Go
                        <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </button>
                </div>
            </div>
        </div>
    );
}
