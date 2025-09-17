// frontend-app/next.config.ts

const nextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
} satisfies import("next").NextConfig;

export default nextConfig;
