import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  reactStrictMode: true,
  webpack: (config, { dev, isServer }) => {
    if (dev && isServer) {
      config.optimization.splitChunks = false
    }
    return config
  },
}

export default nextConfig
