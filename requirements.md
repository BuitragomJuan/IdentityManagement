### REQUIREMENTS FOR THE BUSINESS CASE ###

1. bussines requirements

DemoCompany requires to create a way for the external contratists
to access the company's digital corporate services. (email, internal platforms, official comms, etc.)

2. requeriments of the user

Stakeholders: External contractors, DemoCompany

-- User stories 
External contractors:
AS a external contractor,
I WANT to access the company's digital corporate services
SO THAT I can perform my work efficiently and communicate effectively with DemoCompany.
DemoCompany:
AS a company,
I WANT to provide secured and controlled access to our digital corporate services to external contractors
SO THAT we can ease collaboration and communication with our external contractors.

3. Functional requirements

**R01 - Requirement: CSV file generation**
Given a public JSON service,
When the company uses the application,
Then a CSV file should be generated with transformed data.

**R02- Requirement: contractors information output in CSV file**
Given an external contractor stored in a public JSON service,
When the record is processed successfully,
Then the external contractor's information should be readable
as a register in the generated CSV file
(fields: full name, phone number, original email, company they work for, city, generated email).

**R03 - Requirement: Endpoint connection**
Given an endpoint,
When the application connects to it,
Then the JSON should be obtained and its registers processed by the system

**R04 - Requirement: corporate email generation**
Given an external contractors information,
when the application processes the information,
Then a corporate email should be generated for the external contractor

**R05 - Requirement: email generation format**
Given an external contractor's information,
When the application processes the information,
Then a corporate email should be generated in the following format:
[firstLetterOfFirstNameInLowercase][LastNameInLowercase]@democompany.com (e.g., John Doe -> jdoe@democompany.com)

**R06 - Requirement: email generation format prefixes,sufixxes and initials**
Given an external contractor whose name has a prefix (Sr.,Mr.,Dr., Mrs.), suffix (Jr.,Sr.,II–V) or an initial of a name.
When the applications process this kind of names
Then prefixes, suffixes and single-letter initials are ignored; the first remaining word is the first name and the last remaining word is the last name.
example:
Jane A. Doe -> jdoe
Dr. James Charles V -> jcharles
Mrs. Dennis Schulist → dschulist
Nicholas Runolfsdottir V → nrunolfsdottir
If fewer that two words remain then system will just skip and log. 

**R07 - Requirement: email generation** uniqueness
Given an external contractor's information,
When the application generates an email duplicated,
Then the application should handle duplicates by adding an incremental number (e.g., jdoe1@democompany.com). First occurrence gets no number, the second gets 1, the third 2, and so on.

**R08 - Requirement: Log register**
Given the system,
When the application starts, processes the registers and creates the CSV file,
Then logs should be generated for system monitoring and debugging purposes, logs of:
process start
process runtime
total of register obtained from the endpoint
total of registers correctly processed
confirmation of CSV file generation
any relevant validation

**R09 - Requirement: Allowed characters in naming**
Given the external contractor's name register
When the system manages an username
Then allowed characters must be [a-z0-9]
For names with separation characters, handle by Stripping:
O'Brien → obrien.
While latin names get transliterated
Núñez -> nunez
characters without a decomposition are stripped;

4. Non functional requirements

- Security

**NR01 - Requirement: Validate external input**
 Record's fields must exist and be the expected type before processing, otherwise the record is skipped and logged with its id and reason.

**NR02 - Requirement: Unique contractors identities**
 the generated emails have to be unique per contractor. compared case-insensitively.

**NR03 - Requirement: CSV injections handling**
 neutralize cells that start with characters that could run formulas in CSV with applications like Excel (= + - @, tab, carriage return)

**NR04 - Requirement: Secure transport**
 HTTPS only, certificate verification on, explicit timeout, status code and content type checked.

**NR05 - Requirement: Minimize personal data in logs**
 Logs contain counts, record ids and reasons, never names, phones or emails.

**NR06 - Requirement: Fail safely, with no partial output.**
 On an error, no half-written CSV is left behind. Write to a temp file, then rename it.