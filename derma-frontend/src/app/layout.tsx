import "./globals.css";
import type {ReactNode} from "react";
import DoctorHeader from "../components/DoctorHeader";

export default function RootLayout({children}: {children: ReactNode}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <div className="flex min-h-screen flex-col">
          <DoctorHeader />
          <div className="flex-1">{children}</div>
        </div>
      </body>
    </html>
  );
}
