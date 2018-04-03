#! /usr/bin/python
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def check_report_dict_key(report_dict = None):
	key_list = ['ip_address',
			'qpkg_name',
			'qpkg_version',
			'cloud_service',
			'server_name',
			'server_model',
			'qts_version',
			'local_create_result',
			'local_rename_result',
			'local_move_result',
			'local_edit_result',
			'local_delete_result',
			'cloud_create_result',
			'cloud_rename_result',
			'cloud_move_result',			
			'cloud_delete_result']
	
	for key in key_list:
		if not(report_dict.has_key(key)):
			report_dict[key] = '<center>NA</center>'
		else:
			if report_dict[key] == 'PASS':
				report_dict[key] = '<center style="color: green;">PASS</center>'
			elif report_dict[key] == 'FAIL':
				report_dict[key] = '<center style="color: red;">FAIL</center>'


def send_report(report_dict = None, recipients = None):
	check_report_dict_key(report_dict)	
	username = 'qnapanto.do.not.reply@gmail.com'
	password = 'qnapanto1234'
	fromaddr = 'qnapanto.do.not.reply@gmail.com'
	toaddr = ', '.join(recipients)

	# Create message container - the correct MIME type is multipart/alternative.
	msg = MIMEMultipart('alternative')
	msg['Subject'] = "{} {} Automation BFT report ({})".format(report_dict['qpkg_name'],
																report_dict['qpkg_version'],
																report_dict['cloud_service']
																)
	msg['From'] = fromaddr
	msg['To'] = toaddr

	# Create the body of the message (a plain-text and an HTML version).
	html = """\
	<html>
		<head>
			<style type="text/css">			
				table, th, td {
					font-family: Verdana;
					margin: 0.5em;
					padding: 0.5em 1em 0.5em 1em;
					text-align: left;
				    border: 1px solid black;
				    border-collapse: collapse;
				}
				p {
					font-family: Verdana;
					font-size: 1.2em;
				}
			</style>
		</head>
	"""
	html += """\
		<body>
			<table>
				<tr>
					<th style="background-color: #ADD8E6;" colspan="2">Testing environment</th>								
				</tr>
				<tr>
					<td>IP Address</td>
					<td><a href='http://{0}:8080/cgi-bin/'>{1}</a></td>
				</tr>
				<tr>
					<td>QPKG name</td>
					<td>{2}</td>
				</tr>
				<tr>
					<td>QPKG version</td>
					<td>{3}</td>
				</tr>
				<tr>
					<td>Cloud service</td>
					<td>{4}</td>
				</tr>
				<tr>
					<td>Server name</td>
					<td>{5}</td>
				</tr>
				<tr>
					<td>Server model</td>
					<td>{6}</td>
				</tr>
				<tr>
					<td>QTS version</td>
					<td>{7}</td>
				</tr>
				<tr>
					<th style="background-color: #ADD8E6;" colspan="2">Testing result</th>
				</tr>
				<tr>
					<th style="background-color: #DCDCDC;" colspan="2">LOCAL</th>
				</tr>
				<tr>
					<td>create files/folders</td>
					<td>{8}</td>
				</tr>
				<tr>
					<td>rename files &amp; folders</td>
					<td>{9}</td>
				</tr>
				<tr>
					<td>move files &amp; folders</td>
					<td>{10}</td>
				</tr>
				<tr>
					<td>edit files</td>
					<td>{11}</td>
				</tr>
				<tr>
					<td>delete files &amp; folders</td>
					<td>{12}</td>
				</tr>
				<tr>
					<th style="background-color: #DCDCDC;" colspan="2">CLOUD</th>
				</tr>
				<tr>
					<td>create files/folders</td>
					<td>{13}</td>
				</tr>
				<tr>
					<td>rename files &amp; folders</td>
					<td>{14}</td>
				</tr>
				<tr>
					<td>move files &amp; folders</td>
					<td>{15}</td>
				</tr>							
				<tr>
					<td>delete files &amp; folders</td>
					<td>{16}</td>
				</tr>
			</table>			
			<br>
			<hr>
			<p>
			Note: This is an auto generated email. Please do not reply to this email. 
			If you have questions regarding the content of this email, please send email to mardianto@qnap.com
			</p>
		</body>
	</html>
	""".format(report_dict['ip_address'],
	           report_dict['ip_address'],
	           report_dict['qpkg_name'],
	           report_dict['qpkg_version'],
	           report_dict['cloud_service'],
	           report_dict['server_name'],
	           report_dict['server_model'],
	           report_dict['qts_version'],
	           report_dict['local_create_result'],
	           report_dict['local_rename_result'],
	           report_dict['local_move_result'],
	           report_dict['local_edit_result'],
	           report_dict['local_delete_result'],
	           report_dict['cloud_create_result'],
	           report_dict['cloud_rename_result'],
	           report_dict['cloud_move_result'], 	                    
	           report_dict['cloud_delete_result']
	           )

	# Record the MIME types of both parts - text/plain and text/html.
	part2 = MIMEText(html, 'html')

	# Attach parts into message container.
	msg.attach(part2)

	server = smtplib.SMTP('smtp.gmail.com:587')
	# sendmail function takes 3 arguments: sender's address, recipient's address
	# and message to send - here it is sent as one string.
	server.ehlo()
	server.starttls()
	server.login(username, password)
	server.sendmail(fromaddr, recipients, msg.as_string())
	server.quit()