const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = 3030;
const LEADS_FILE = path.join(__dirname, 'data', 'leads.json');
const SITES_DIR = path.join(__dirname, 'generated-sites');

// Ensure data and generated-sites dirs exist
fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });
fs.mkdirSync(SITES_DIR, { recursive: true });

// Initialize leads file if needed
if (!fs.existsSync(LEADS_FILE)) {
    fs.writeFileSync(LEADS_FILE, '[]');
}

const mimeTypes = {
    '.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
    '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
};

function getLeads() {
    return JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
}

function saveLeads(leads) {
    fs.writeFileSync(LEADS_FILE, JSON.stringify(leads, null, 2));
}

function readBody(req) {
    return new Promise((resolve) => {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => resolve(body));
    });
}

function generateSite(lead) {
    const slug = lead.business.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+$/, '');
    const siteDir = path.join(SITES_DIR, slug);
    fs.mkdirSync(siteDir, { recursive: true });

    // Read restaurant template and customize it
    const templateHtml = fs.readFileSync(path.join(__dirname, 'templates', 'restaurant', 'index.html'), 'utf8');
    const templateCss = fs.readFileSync(path.join(__dirname, 'templates', 'restaurant', 'style.css'), 'utf8');

    // Replace placeholder content with client info
    let html = templateHtml
        .replace(/Bella's Italian Kitchen/g, lead.business)
        .replace(/Bella's/g, lead.business.split(' ')[0].replace(/'s$/, '') + "'s")
        .replace(/Authentic Italian Dining/g, lead.business + ' — Official Website')
        .replace(/Authentic Italian,<br>Made with Love/g, `Welcome to<br>${lead.business}`)
        .replace(/Fresh pasta, wood-fired pizza, and family recipes passed down for generations\./g,
            lead.message || 'Quality food and great service for our community.')
        .replace(/EST\. 2010/g, 'EST. 2024')
        .replace(/\(555\) 123-4567/g, lead.phone || '(555) 000-0000')
        .replace(/hello@bellasitaliankitchen\.com/g, lead.email || '')
        .replace(/123 Main Street/g, lead.address || '123 Main Street')
        .replace(/Your City, ST 12345/g, lead.city || 'Your City, ST 12345')
        .replace(/<a href="#">MichaWeb<\/a>/g, '<a href="http://localhost:3030">MichaWeb</a>');

    fs.writeFileSync(path.join(siteDir, 'index.html'), html);
    fs.writeFileSync(path.join(siteDir, 'style.css'), templateCss);

    return slug;
}

const server = http.createServer(async (req, res) => {
    const parsed = url.parse(req.url, true);
    const pathname = parsed.pathname;

    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

    // === API ROUTES ===

    // Submit a new lead (from contact form)
    if (pathname === '/api/leads' && req.method === 'POST') {
        const body = JSON.parse(await readBody(req));
        const leads = getLeads();
        const lead = {
            id: Date.now(),
            name: body.name || '',
            business: body.business || '',
            phone: body.phone || '',
            email: body.email || '',
            service: body.service || '',
            message: body.message || '',
            address: body.address || '',
            city: body.city || '',
            status: 'new',
            siteSlug: null,
            createdAt: new Date().toISOString(),
        };
        leads.push(lead);
        saveLeads(leads);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, message: 'Thanks! We\'ll get back to you within 24 hours.' }));
        console.log(`NEW LEAD: ${lead.name} — ${lead.business} — ${lead.phone}`);
        return;
    }

    // Get all leads
    if (pathname === '/api/leads' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(fs.readFileSync(LEADS_FILE));
        return;
    }

    // Generate a site for a lead
    if (pathname === '/api/generate' && req.method === 'POST') {
        const body = JSON.parse(await readBody(req));
        const leads = getLeads();
        const lead = leads.find(l => l.id === body.leadId);
        if (!lead) { res.writeHead(404); res.end('Lead not found'); return; }

        const slug = generateSite(lead);
        lead.status = 'site-ready';
        lead.siteSlug = slug;
        saveLeads(leads);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, slug, url: `http://localhost:3030/sites/${slug}/` }));
        console.log(`SITE GENERATED: ${lead.business} → /sites/${slug}/`);
        return;
    }

    // Update lead status
    if (pathname === '/api/lead-status' && req.method === 'POST') {
        const body = JSON.parse(await readBody(req));
        const leads = getLeads();
        const lead = leads.find(l => l.id === body.leadId);
        if (!lead) { res.writeHead(404); res.end('Lead not found'); return; }
        lead.status = body.status;
        saveLeads(leads);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true }));
        return;
    }

    // === FILE SERVING ===

    // Serve generated sites
    if (pathname.startsWith('/sites/')) {
        const sitePath = pathname.replace('/sites/', '');
        let filePath = path.join(SITES_DIR, sitePath);
        if (filePath.endsWith('/') || !path.extname(filePath)) {
            filePath = path.join(filePath, 'index.html');
        }
        // Prevent directory traversal
        if (!filePath.startsWith(SITES_DIR)) { res.writeHead(403); res.end('Forbidden'); return; }
        return serveFile(filePath, res);
    }

    // Serve agency site
    if (pathname.startsWith('/agency/')) {
        const filePath = path.join(__dirname, 'my-agency', pathname.replace('/agency/', ''));
        return serveFile(filePath, res);
    }

    // Serve dashboard
    if (pathname === '/' || pathname === '/dashboard') {
        return serveFile(path.join(__dirname, 'dashboard', 'index.html'), res);
    }
    if (pathname.startsWith('/dashboard/')) {
        return serveFile(path.join(__dirname, 'dashboard', pathname.replace('/dashboard/', '')), res);
    }

    res.writeHead(404);
    res.end('Not found');
});

function serveFile(filePath, res) {
    const ext = path.extname(filePath).toLowerCase();
    const contentType = mimeTypes[ext] || 'text/html';
    try {
        const data = fs.readFileSync(filePath);
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(data);
    } catch {
        res.writeHead(404);
        res.end('Not found');
    }
}

server.listen(PORT, () => {
    console.log('');
    console.log('===========================================');
    console.log('  MichaWeb Agency Server Running!');
    console.log('===========================================');
    console.log(`  Dashboard:  http://localhost:${PORT}/`);
    console.log(`  Agency Site: http://localhost:${PORT}/agency/`);
    console.log('===========================================');
    console.log('');
    console.log('Waiting for leads...');
});
