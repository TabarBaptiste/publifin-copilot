"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Shell.module.css";

const LINKS = [
  { href: "/", label: "Questions" },
  { href: "/analyses", label: "Pré-analyse" },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Navigation principale" className={styles.nav}>
      {LINKS.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={styles.navLink}
          aria-current={pathname === link.href ? "page" : undefined}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
