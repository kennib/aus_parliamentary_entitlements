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
	headers = [[line
			for line in pdf.pq(page+' *:in_bbox("{}, {}, {}, {}")'.format(*box))
			if line.text
		] for box in header_rects]
	
	return headers

def get_table_data(header_line, table_line):
	data = {header.text.strip(): None for header in header_line}
	for header in header_line:
		for datum in table_line:
			if float(datum.get('x0')) >= float(header.get('x0'))-5 \
			and float(datum.get('x0')) <= float(header.get('x1'))+5:
				data[header.text.strip().lower()] = datum.text.strip()
	
	return data

data = []
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

		# Initial table data
		table = None
		category = []
		headers = get_headers(pdf, page)
		is_first_heading = True
		header_line = None

		# Find the table data
		for y, line in sorted_lines:
			line_text = [box.text.strip() for box in line.values()]
			table_data = get_table_data(header_line, line.values()) if header_line else {}

			#  Are we reading a heading, table header or table data?
			is_table_header = line.values() in headers
			is_table_data = not (is_first_heading or ('amount' in table_data and table_data['amount'] is None))
			is_heading = not (is_table_header or is_table_data)

			# If at a heading then add to the category list
			if is_heading:
				if is_first_heading:
					category += line_text
				else:
					subcategory = line_text
			
			# If at a table header then initialize table data
			elif is_table_header:
				header_line = line.values()
				if is_first_heading:
						is_first_heading = False
						subcategory = category[-1:]
						category = category[:-1]
			
			# If at table data the append to the table
			elif is_table_data:
				table_data['date'], table_data['name'], data_kind, table_data['category'] = (category+subcategory)[:4]
				table_data['subcategory'], = subcategory if len(category+subcategory) >= 5 else [None]
				if 'Transaction Details' in data_kind:
					data.append(table_data)

for datum in data:
	print datum

# Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
