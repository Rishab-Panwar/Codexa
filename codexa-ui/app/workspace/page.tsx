"use client";

import React, { useState, useEffect } from "react";
import AppLayout from "@/components/Layout/AppLayout";
import Sidebar from "@/components/Sidebar/Sidebar";
import ChatWindow from "@/components/Chat/ChatWindow";
import ContextPanel from "@/components/Panels/ContextPanel";
import WelcomeModal from "@/components/WelcomeModal";
import FilePreviewModal from "@/components/FilePreviewModal";
import KeyboardShortcutsHelp from "@/components/KeyboardShortcutsHelp";

export default function WorkspacePage() {
    const [previewFile, setPreviewFile] = useState<string | null>(null);

    // Listen for file preview events from RepoTree and ContextPanel
    useEffect(() => {
        const handler = (e: Event) => {
            const path = (e as CustomEvent).detail?.path;
            if (path) setPreviewFile(path);
        };
        window.addEventListener("codexa:preview-file", handler);
        return () => window.removeEventListener("codexa:preview-file", handler);
    }, []);

    return (
        <>
            <WelcomeModal />
            <KeyboardShortcutsHelp />
            <FilePreviewModal
                filePath={previewFile}
                onClose={() => setPreviewFile(null)}
            />
            <AppLayout
                sidebar={<Sidebar />}
                chat={<ChatWindow />}
                panels={<ContextPanel />}
            />
        </>
    );
}
