import scraperwiki
import lxml.html
import urllib2
import pdfquery

from StringIO import StringIO
from collections import defaultdict

ENTITLEMENTS_PAGE = "http://www.finance.gov.au/publications/parliamentarians-reporting/parliamentarians-expenditure-P34/"

# Read in a page
html = scraperwiki.scrape(ENTITLEMENTS_PAGE)

# Find list of links to expense reports on the page using css selectors
root = lxml.html.fromstring(html)
links = root.cssselect("tr td:first-child a")
urls = [link.get('href') for link in links]

# Download the PDFs
pdfs = [pdfquery.PDFQuery(StringIO(urllib2.urlopen(url).read())) for url in urls[:1]]
for pdf in pdfs: pdf.load()

# Find the relevant information in the PDFs
def get_headers(pdf, page):
	# Find all the rects
       	rects = pdf.pq(page+' LTRect')
	
	# Group the rects into horizontal lines
	horizontal_rects = defaultdict(list)
	for rect in rects:
		horizontal_rects[rect.get('y0'), rect.get('y1')].append(rect)

	# Get the extent of the header rects
	header_rects = [
		( min([float(rect.get('x0')) for rect in header])
		, min([float(rect.get('y0')) for rect in header])
		, max([float(rect.get('x1')) for rect in header])
		, max([float(rect.get('y1')) for rect in header])
		) for header in horizontal_rects.values()]

	# Find the text in all the text boxes
	headers = [[line.text.strip()
			for line in pdf.pq(page+' *:in_bbox("{}, {}, {}, {}")'.format(*box))
			if line.text
		] for box in header_rects]
	
	return headers

tables = defaultdict(dict)
for pdf in pdfs:
	num_pages = pdf.doc.catalog['Pages'].resolve()['Count']
	for page in range(num_pages):
		page = 'LTPage[pageid="{}"]'.format(page)
		# Find all the text
		texts = [box for box in pdf.pq(page+' *') if box.text]
		
		# Group the text into horizontal lines
		lines = defaultdict(dict)
		for text in texts:
			lines[float(text.get('y0'))][float(text.get('x0'))] = text
		
		# Sort the lines
		sorted_lines = sorted(lines.items())[::-1]

		# Find the table data
		category = []
		headers = get_headers(pdf, page)
		header_line = None
		before_headers = True
		for y, line in sorted_lines:
			# Find the category of the table
			if before_headers:
				line_text = [box.text.strip() for x, box in sorted(line.items()) if box.text]
				if line_text in headers:
					before_headers = False
					header_line = line.values()
					category = tuple(category)
					tables[category]['data'] = []
				else:
					category += line_text

			# Get each line of the table
			else:
				table_line = {}
				for x, box in line.items():
					for header in header_line:
						if x >= float(header.get('x0')) and x <= float(header.get('x1')):
							table_line[header.text.strip()] = box.text.strip()
						if header not in table_line:
							header = None

				tables[category]['data'].append(table_line)

		print page
		for y, line in sorted_lines:
			print [box.text.strip() for box in line.values()]
			print line.values()
			print
		print "-"*30

for category in tables:
	print category
	for datum in tables[category]['data']:
		print datum
	print
# Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
