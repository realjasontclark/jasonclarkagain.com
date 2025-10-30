import { PropsWithChildren } from "react";

type CardProps = PropsWithChildren<{ title: string; actions?: React.ReactNode; subtitle?: string }>;

export default function Card({ title, subtitle, actions, children }: CardProps) {
  return (
    <section
      style={{
        background: "rgba(15, 23, 42, 0.75)",
        borderRadius: "16px",
        padding: "24px",
        border: "1px solid rgba(148, 163, 184, 0.2)",
        display: "flex",
        flexDirection: "column",
        gap: "16px"
      }}
    >
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "1.2rem", fontWeight: 600 }}>{title}</h2>
          {subtitle && <p style={{ fontSize: "0.9rem", color: "#94a3b8" }}>{subtitle}</p>}
        </div>
        {actions}
      </header>
      <div>{children}</div>
    </section>
  );
}
