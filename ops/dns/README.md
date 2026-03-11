# DNS (Cloudflare)

## Zones
- `gestiqcloud.com` on Cloudflare.

## Relevant Records
- `admin.gestiqcloud.com` and `www.gestiqcloud.com` CNAME/A records point to the Worker or Render target, depending on the current setup.
- Additional subdomains are listed in `gestiqcloud.com.txt`, `cloudflare_dns_records.txt`, and `gestiqcloud.com.cname-flattening.txt`.

## Operations
- Apply changes through the Cloudflare dashboard or API.
- Keep Worker routes aligned with the published DNS records.
- Document TTL and proxy mode settings per environment.
