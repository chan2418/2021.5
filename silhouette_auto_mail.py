#!/usr/bin/python3
"""
This module is used for internal notications.
we can use this module for any software which supports python.

"""

# default module
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP

try:
    from email import encoders
    from email.MIMEBase import MIMEBase
except:
    pass

import logging

logging.basicConfig(level=logging.DEBUG)


__author__ = ["Badri Gs (badri.narayanan@basilicfly.com)"]
__email__ = "pipeline@basilicfly.com"


class CreateMail(object):
    """
    CreateMail SMTP instance.

    InternalMail is the class to send a notification to
    given user.

    internal mail IP address: xx.xx.xx.xx:xx

    Note: we are restricted the BCC mail.

    >>> in_mail = CreateMail(
        org_domain=os.environ.get("ORG_DOMAIN", "basilicfly.com"),
        host=os.environ.get("MAIL_HOST", ""),
        port=os.environ.get("MAIL_PORT", 25),
        username=os.environ.get("MAIL_USERNAME", "badri.narayanan"),
        password=os.environ.get("MAIL_pas", "7089057731011752499"),
    )
    >>> in_mail.to_address = "xyz"
    >>> in_mail.cc_address = "abc"
    >>> in_mail.subject = "Test Mail"
    >>> in_mail.append_body("Hi, \ntesting mail") # plain text
    >>> in_mail.append_body("<p>Vanakkam</p>") # html text

    >>> print (str(in_mail))
    >>> in_mail.send_mail()

    """

    def __init__(self, *args, **kwargs):
        self._host = kwargs.get("host", "172.168.1.10")
        self._port = kwargs.get("port", 25)
        self._username = kwargs.get("username", "no-reply@basilicfly.co")
        self._password = kwargs.get("password", "bfs@12345678")
        self.org_domain = kwargs.get("org_domain", "basilicfly.co")
        self._subject = None
        self._to_addresses = []
        self._to_cc = []
        self.body = MIMEMultipart("alternative")

        # logging
        self.logger = logging.getLogger("com.org.send-internal-mail")
        print(self._username)
        print(self._password)

        _checks = [
            self.org_domain is not None,
            self._host is not None,
            self._port is not None,
            self._username is not None,
            self._password is not None,
        ]

        if not all(_checks):
            raise ValueError("missing org_domain | host | port | username | password.")

    def __str__(self):
        return """
        To: {}
        CC: {}
        Subject: {}
        Body: {}
        """.format(self.to_address, self.cc_address, self.subject, self.body)

    def check_and_correct_email_addresses(self, mail_address):
        if isinstance(mail_address, str):
            # this will return only the name
            if mail_address.find("@{0}".format(self.org_domain)) == -1:
                return "{0}@{1}".format(mail_address.split("@")[0], self.org_domain)
            else:
                return mail_address
        elif isinstance(mail_address, list):
            _results = []
            for each in mail_address:
                if each.find("@{0}".format(self.org_domain)) == -1:
                    _results.append(
                        "{0}@{1}".format(each.split("@")[0], self.org_domain)
                    )
                else:
                    _results.append(each)
            return _results
        else:
            self.logger.error("Please give the valid mail ID.")
            raise ValueError(
                "expected `str` or `list` found: `{0}`".format(type(mail_address))
            )

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, _subject):
        if isinstance(_subject, str):
            self._subject = _subject
            self.logger.debug("subject: {}".format(_subject))
        else:
            self.logger.error("Excepted `str` but given {}".format(type(_subject)))
            raise TypeError("Excepted `str` but given {}".format(type(_subject)))

    @property
    def to_address(self):
        return self._to_addresses

    @to_address.setter
    def to_address(self, _data):
        self.logger.debug(
            "Added {}".format(self.check_and_correct_email_addresses(_data))
        )
        if isinstance(_data, str):
            self._to_addresses.append(self.check_and_correct_email_addresses(_data))
            self.logger.debug("Added {}".format(_data))
        elif isinstance(_data, list):
            self.logger.debug("test {}".format(_data))
            self._to_addresses.extend(self.check_and_correct_email_addresses(_data))
            self.logger.debug("Added {}".format(_data))
        else:
            self.logger.error("Invalid To Address, required `str` or `list`.")
            raise TypeError("Invalid To Address, required `str` or `list`.")

    @property
    def cc_address(self):
        return self._to_cc

    @cc_address.setter
    def cc_address(self, _data):
        if isinstance(_data, str):
            self._to_cc.append(self.check_and_correct_email_addresses(_data))
            self.logger.debug("Added {}".format(_data))
        elif isinstance(_data, list):
            self._to_cc.extend(_data)
            self.logger.debug(
                "Added {}".format(self.check_and_correct_email_addresses(_data))
            )
        else:
            self.logger.error("Invalid CC Address, required `str` or `list`.")
            raise TypeError("Invalid CC Address, required `str` or `list`.")

    def append_body(self, _body, _mode="plain"):
        if not isinstance(_body, str):
            raise ValueError("Please Give the `str` data.")
        # check if content is html
        if bool(re.search(r"<\/?[a-z][\s\S]*>", _body)) or _mode == "html":
            self.body.attach(MIMEText(_body, "html"))
        else:
            self.body.attach(MIMEText(_body, "plain"))

        self.logger.debug("body: {}".format(_body))

    def set_attachment(self, file):
        assert os.path.exists(file)
        attachment = open(file, "rb")

        part = MIMEBase("application", "octet-stream")
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", "attachment; filename= %s" % os.path.basename(file)
        )

        self.body.attach(part)

    def send_mail(self):
        """
        SMTP Mail sender
        """

        _checks = [self.subject is not None, len(self.to_address), len(self.cc_address)]

        if not all(_checks):
            self.logger.error(
                "missing data: provide all the data like (to_address, subject, body)."
            )
            raise ValueError(
                "missing data: provide all the data like (to_address, subject, body)."
            )
        try:
            self.logger.info(self.to_address)
            self.body["Subject"] = self.subject
            self.body["From"] = self._username
            self.body["To"] = ", ".join(self.to_address)
            self.body["Cc"] = ", ".join(self.cc_address)
            self.body["Bcc"] = ""
            server = SMTP(self._host, self._port)
            server.starttls()
            server.set_debuglevel(1)
            server.ehlo()
            if server.has_extn("auth"):
                server.login(
                    self._username.split("@")[0], 
                    self._password
                )
            else:
                self.logger.warning("SMTP Auth not supported - sending without login.")
            try:    
                server.send_message(self.body)
            except Exception:    
                server.sendmail(
                    self._username,
                    self.to_address + self.cc_address,
                    self.body.as_string()
                )
                server.quit()
                print("Mail sent...")
        except Exception as _error:
            raise _error

