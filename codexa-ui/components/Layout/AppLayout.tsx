"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import TopBar from "./TopBar";

interface AppLayoutProps {
    sidebar: React.ReactNode;
    chat: React.ReactNode;
    panels: React.ReactNode;
}

export default function AppLayout({ sidebar, chat, panels }: AppLayoutProps) {
    // Explorer open by default; context panel collapsed so chat is the focus.
    const [leftOpen, setLeftOpen] = useState(true);
    const [rightOpen, setRightOpen] = useState(false);

    // Ctrl+B toggles the explorer drawer.
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.ctrlKey && e.key === "b") {
                e.preventDefault();
                setLeftOpen((v) => !v);
            }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, []);

    return (
        <div className="flex flex-col h-screen w-full overflow-hidden bg-background text-foreground font-sans">
            <TopBar
                leftOpen={leftOpen}
                rightOpen={rightOpen}
                onToggleLeft={() => setLeftOpen((v) => !v)}
                onToggleRight={() => setRightOpen((v) => !v)}
            />

            <div className="flex flex-1 min-h-0 overflow-hidden">
                {/* Left drawer — Explorer + Quick Starters */}
                <aside
                    className={cn(
                        "flex-shrink-0 border-r border-border bg-sidebar overflow-hidden transition-[width] duration-200 ease-out",
                        leftOpen ? "w-64" : "w-0",
                    )}
                >
                    <div className="w-64 h-full overflow-y-auto">{sidebar}</div>
                </aside>

                {/* Center — Chat (the focus) */}
                <main className="flex-1 flex flex-col min-w-0 bg-background">{chat}</main>

                {/* Right drawer — Context / Graph / History */}
                <aside
                    className={cn(
                        "flex-shrink-0 border-l border-border bg-background overflow-hidden transition-[width] duration-200 ease-out",
                        rightOpen ? "w-80" : "w-0",
                    )}
                >
                    <div className="w-80 h-full overflow-y-auto">{panels}</div>
                </aside>
            </div>
        </div>
    );
}
