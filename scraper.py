import scraperwiki
import lxml.html
import urllib2
import pdfquery

from StringIO import StringIO
from collections import defaultdict
import datetime

ENTITLEMENTS_PAGE = "http://www.finance.gov.au/publications/parliamentarians-reporting/parliamentarians-expenditure-P34/"

# Read in a page
html = scraperwiki.scrape(ENTITLEMENTS_PAGE)

# Find list of links to expense reports on the page using css selectors
root = lxml.html.fromstring(html)
links = root.cssselect("tr td:first-child a")
urls = [link.get('href') for link in links]

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

def read_pdf(pdf):
	num_pages = pdf.doc.catalog['Pages'].resolve()['Count']
	for page in range(num_pages):
		pdf.load(page)
		print "Page {:02}".format(page)

		page = 'LTPage[pageid="{}"]'.format(page+1)
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
		metadata = []
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
				# For the first heading all of the metadata is relevant
				if is_first_heading:
					metadata += line_text
				# Subsequent metadata is all of the previous metadata except the last heading
				else:
					metadata = metadata[:-1] + line_text
			
			# If at a table header then initialize table data
			elif is_table_header:
				header_line = line.values()
				if is_first_heading:
						is_first_heading = False
			
			# If at table data the append to the table
			elif is_table_data:
				# Get metadata
				report_date, name, data_kind, category = metadata[:4]
				subcategory = metadata[4] if len(metadata) >= 5 else None

				# Parse dates
				report_date_from = report_date.split('to ')[0]+report_date[-4:]
				report_date_from = datetime.datetime.strptime(report_date_from, '%d %B %Y').date()
				report_date_to = report_date.split('to ')[1]
				report_date_to = datetime.datetime.strptime(report_date_to, '%d %B %Y').date()

				# Parse numerical values
				if table_data.get('amount'):
					table_data['amount'] = table_data['amount'].translate(None, '$,^*')

				# Add to table data
				table_data.update({
					'name': name,
					'report_date_from': report_date_from.isoformat(),
					'report_date_to': report_date_to.isoformat(),
					'category': category,
					'subcategory': subcategory
				})

				if 'Transaction Details' in data_kind and table_data.get('details', '') != '' and table_data.get('details') != 'Aggregated Total':
					# Write out to the sqlite database using scraperwiki library
					scraperwiki.sqlite.save(unique_keys=['name', 'category', 'subcategory', 'details', 'report_date_from', 'report_date_to'], data=table_data)

# Download and read each PDF url
for url in urls:
	print url

	# Download the PDF
	pdf = pdfquery.PDFQuery(StringIO(urllib2.urlopen(url).read()))

	# Extract data
	read_pdf(pdf)

	del pdf
