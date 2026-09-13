import TopBar from "@/components/layout/TopBar";

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex flex-col h-screen" style={{ backgroundColor: "var(--bg-base)" }}>
      <TopBar />
      <main className="flex-1 min-h-0">{children}</main>
    </div>
  );
}
