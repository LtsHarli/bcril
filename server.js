const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');
const puppeteer = require('puppeteer');
const { URL } = require('url');

const app = express();
const port = 80;

// Path to your Chromium or Chrome executable
const executablePath = '/usr/bin/chromium-browser'; // or '/usr/bin/google-chrome' for Google Chrome

app.use(express.static(__dirname));

app.get('/bcril', async (req, res) => {
    const url = req.query.url;
    const downloadLinks = req.query.href === 'true'; // Check if href links should be downloaded

    if (!url) {
        return res.status(400).json({ error: 'Please provide a URL using the query parameter ?url=' });
    }

    console.log(`Received request to scrape: ${url}`);
    console.log(`Download links: ${downloadLinks}`);

    try {
        console.log('Launching browser...');
        const browser = await puppeteer.launch({
            executablePath,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        console.log('Browser launched.');

        const page = await browser.newPage();
        await page.goto(url, { waitUntil: 'networkidle2' });

        const html = await page.content();
        const $ = cheerio.load(html);

        const resources = [];

        // Collect CSS, JS, and image resources
        $('link[rel="stylesheet"]').each((i, elem) => {
            const cssUrl = $(elem).attr('href');
            if (cssUrl) resources.push({ url: cssUrl, type: 'css' });
        });

        $('script[src]').each((i, elem) => {
            const jsUrl = $(elem).attr('src');
            if (jsUrl) resources.push({ url: jsUrl, type: 'js' });
        });

        $('img[src]').each((i, elem) => {
            const imgUrl = $(elem).attr('src');
            if (imgUrl) resources.push({ url: imgUrl, type: 'img' });
        });

        // Download and embed resources directly in the HTML content
        console.log('Processing resources...');
        for (let resource of resources) {
            try {
                const resourceUrl = new URL(resource.url, url).href;
                console.log(`Processing ${resourceUrl}`);
                const resourceData = await axios.get(resourceUrl, { responseType: 'arraybuffer' });

                if (resource.type === 'img') {
                    const base64 = resourceData.data.toString('base64');
                    const mimeType = resourceData.headers['content-type'];
                    $(`[src="${resource.url}"]`).attr('src', `data:${mimeType};base64,${base64}`);
                } else {
                    $(`[src="${resource.url}"], [href="${resource.url}"]`).attr(resource.type === 'img' ? 'src' : 'href', resourceUrl);
                }
            } catch (resourceError) {
                console.error(`Error processing resource ${resource.url}:`, resourceError);
            }
        }

        // Process linked pages if `href=true`
        if (downloadLinks) {
            console.log('Processing linked pages...');
            const links = [];
            $('a[href]').each((i, elem) => {
                const href = $(elem).attr('href');
                const linkUrl = new URL(href, url).href;
                if (!links.includes(linkUrl) && linkUrl.startsWith(url)) {
                    links.push(linkUrl);
                }
            });

            for (let link of links) {
                try {
                    console.log(`Downloading linked page ${link}`);
                    const linkedPage = await axios.get(link);
                    const linkedHtml = linkedPage.data;
                    const linked$ = cheerio.load(linkedHtml);

                    // Save linked content as a base64 string if needed (similar processing to the main page)
                    // Note: Depending on the requirements, you might need additional processing here

                } catch (linkError) {
                    console.error(`Error downloading linked page ${link}:`, linkError);
                }
            }
        }

        await browser.close();
        console.log('Scraping complete!');

        // Send the HTML content directly to the client
        res.setHeader('Content-disposition', 'attachment; filename=index.html');
        res.setHeader('Content-type', 'text/html');
        res.send($.html());
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: 'An error occurred while processing your request.' });
    }
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
