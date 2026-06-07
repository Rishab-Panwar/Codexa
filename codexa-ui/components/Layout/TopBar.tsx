"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Code2, PanelLeft, PanelRight, BarChart3, Home } from "lucide-react";
import { cn } from "@/lib/utils";

interface TopBarProps {
    leftOpen: boolean;
    rightOpen: boolean;
    onToggleLeft: () => void;
    onToggleRight: () => void;
}

export default function TopBar({ leftOpen, rightOpen, onToggleLeft, onToggleRight }: TopBarProps) {
    const [repoName, setRepoName] = useState<string | null>(null);

    useEffect(() => {
        const update = () => {
            const name = localStorage.getItem("current_repo_name");
            const id = localStorage.getItem("current_repo_id");
            setRepoName(name || (id ? "Repository" : null));
        };
        update();
        window.addEventListener("codexa:repo-switched", update);
        return () => window.removeEventListener("codexa:repo-switched", update);
    }, []);

    return (
        <header className="flex items-center justify-between h-12 px-3 border-b border-border bg-sidebar flex-shrink-0 z-20">
            {/* Brand + active repo */}
            <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg brand-gradient flex items-center justify-center">
                        <Code2 className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-sm font-semibold brand-text">Codexa</span>
                </div>
                {repoName && (
                    <span className="text-[11px] mono text-muted px-2 py-1 bg-white/5 rounded border border-border truncate max-w-[220px]">
                        {repoName}
                    </span>
                )}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-1">
                <button
                    onClick={onToggleLeft}
                    title="Toggle Explorer (Ctrl+B)"
                    className={cn(
                        "p-1.5 rounded hover:bg-white/5 transition-colors",
                        leftOpen ? "text-accent" : "text-muted",
                    )}
                >
                    <PanelLeft className="w-4 h-4" />
                </button>
                <button
                    onClick={onToggleRight}
                    title="Toggle Context panel"
                    className={cn(
                        "p-1.5 rounded hover:bg-white/5 transition-colors",
                        rightOpen ? "text-accent" : "text-muted",
                    )}
                >
                    <PanelRight className="w-4 h-4" />
                </button>
                <div className="w-px h-5 bg-border mx-1" />
                <Link
                    href="/"
                    title="Home"
                    className="p-1.5 rounded hover:bg-white/5 text-muted hover:text-accent transition-colors"
                >
                    <Home className="w-4 h-4" />
                </Link>
                <Link
                    href="/eval"
                    title="Eval Dashboard"
                    className="p-1.5 rounded hover:bg-white/5 text-muted hover:text-accent transition-colors"
                >
                    <BarChart3 className="w-4 h-4" />
                </Link>
            </div>
        </header>
    );
}
