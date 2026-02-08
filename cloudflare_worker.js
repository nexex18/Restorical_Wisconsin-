// Wisconsin DNR BRRTS Document Scraper Worker
//
// Deploy: Paste this into the Cloudflare Workers dashboard editor
//
// Documents are loaded via AJAX on the detail page. The AJAX endpoints
// require cookies from the initial page load, so we:
// 1. Fetch the main detail page (gets session cookies)
// 2. Use those cookies to fetch the document AJAX endpoints
//
// Usage:
//   GET /               -> Health check
//   GET /?dsn=20001     -> Fetch documents for DSN 20001

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const dsn = url.searchParams.get("dsn");

    if (!dsn) {
      return new Response(JSON.stringify({
        success: true,
        message: "Wisconsin DNR document proxy. Pass ?dsn=NUMBER to fetch documents."
      }), {
        headers: { "content-type": "application/json", "access-control-allow-origin": "*" }
      });
    }

    if (!/^\d+$/.test(dsn)) {
      return new Response(JSON.stringify({
        success: false, error: "dsn must be a numeric value"
      }), {
        status: 400,
        headers: { "content-type": "application/json", "access-control-allow-origin": "*" }
      });
    }

    const baseHeaders = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.5",
    };

    try {
      // Step 1: Fetch the main detail page to get session cookies
      const detailUrl = `https://apps.dnr.wi.gov/rrbotw/botw-activity-detail?dsn=${dsn}`;
      const detailResp = await fetch(detailUrl, { headers: baseHeaders, redirect: "manual" });

      // Collect Set-Cookie headers
      const cookies = detailResp.headers.getAll ?
        detailResp.headers.getAll("set-cookie") :
        [detailResp.headers.get("set-cookie")].filter(Boolean);

      // Also get cookies from the response (Cloudflare Workers handle cookies differently)
      const cookieStr = cookies.map(c => c.split(";")[0]).join("; ");

      // Read the detail page body (needed to consume the response)
      const detailHtml = await detailResp.text();
      const detailStatus = detailResp.status;

      // Step 2: Fetch AJAX endpoints with cookies and referer
      const ajaxHeaders = {
        ...baseHeaders,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": detailUrl,
        "Cookie": cookieStr,
      };

      const [siteFilesResp, addtlDocsResp, actionsResp] = await Promise.all([
        fetch(`https://apps.dnr.wi.gov/rrbotw/BrrtsOnTheWeb/WizSiteFiles?dsn=${dsn}`, {
          headers: ajaxHeaders
        }),
        fetch(`https://apps.dnr.wi.gov/rrbotw/BrrtsOnTheWeb/WizAddtionalURLsDocs?dsn=${dsn}`, {
          headers: ajaxHeaders
        }),
        fetch(`https://apps.dnr.wi.gov/rrbotw/BrrtsOnTheWeb/WizActions?dsn=${dsn}`, {
          headers: ajaxHeaders
        }),
      ]);

      const siteFilesHtml = await siteFilesResp.text();
      const addtlDocsHtml = await addtlDocsResp.text();
      const actionsHtml = await actionsResp.text();

      return new Response(JSON.stringify({
        success: true,
        dsn: dsn,
        detail_status: detailStatus,
        site_files_html: siteFilesHtml,
        site_files_status: siteFilesResp.status,
        addtl_docs_html: addtlDocsHtml,
        addtl_docs_status: addtlDocsResp.status,
        actions_html: actionsHtml,
        actions_status: actionsResp.status,
        cookies_found: cookies.length,
      }), {
        headers: { "content-type": "application/json", "access-control-allow-origin": "*" }
      });
    } catch (error) {
      return new Response(JSON.stringify({
        success: false, dsn: dsn, error: error.message
      }), {
        status: 502,
        headers: { "content-type": "application/json", "access-control-allow-origin": "*" }
      });
    }
  },
};
