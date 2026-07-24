import Image from "next/image";

const SIZES = {
  sm: { width: 130, height: 36 },
  md: { width: 173, height: 48 },
  lg: { width: 231, height: 64 },
} as const;

export default function Logo({ size = "md" }: { size?: keyof typeof SIZES }) {
  const { width, height } = SIZES[size];
  return (
    // The logo's wordmark text is dark navy, so it needs a light backing to stay
    // readable in dark mode regardless of where it's placed.
    <span className="inline-block rounded-lg bg-white p-2 shadow-sm">
      <Image src="/logo.png" alt="Liwa International School" width={width} height={height} priority />
    </span>
  );
}
