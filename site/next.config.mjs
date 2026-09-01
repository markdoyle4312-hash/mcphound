/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  // Already Next's default — set explicitly so it stays true even if that
  // default ever changes. Reputation findings shouldn't ship a readable
  // source map of how the scoring/UI code works.
  productionBrowserSourceMaps: false,
};

export default nextConfig;
