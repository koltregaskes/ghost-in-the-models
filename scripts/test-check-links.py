import importlib.util
import unittest
from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import BaseHandler, ProxyHandler, Request, build_opener
from urllib.response import addinfourl
spec=importlib.util.spec_from_file_location('links','scripts/check-links.py')
links=importlib.util.module_from_spec(spec); spec.loader.exec_module(links)
class LinkChecks(unittest.TestCase):
    def test_actual_references_and_fragments(self):
        p=links.References(); p.feed("<link rel='preconnect' href='https://fonts.example'><a href='guide.pdf#page=2'>Download</a><h2 id='part'>Part</h2><img srcset='small.png 1x, big.png 2x' alt='Chart'>")
        self.assertEqual(p.refs,['guide.pdf#page=2','small.png','big.png']); self.assertIn('part',p.ids)
    def test_redirects_reject_downgrade_and_private_targets(self):
        for target in ['http://public.example/path','https://127.0.0.1/path','https://user:pass@public.example/path','file:///tmp/file']:
            with self.assertRaises(links.UnsafeRedirect): links.SafeRedirects().redirect_request(Request('https://public.example/'),None,302,'Found',{},target)
    def test_file_redirect_is_unsafe_through_full_opener(self):
        # Exercise urllib's error handler, not just redirect_request directly.
        # A synthetic HTTPS response keeps this regression entirely network-free.
        for code in (301,302,303,307,308):
            for header in ('Location','URI'):
                with self.subTest(code=code,header=header):
                    class RedirectFixture(BaseHandler):
                        handler_order=100
                        def https_open(self,request):
                            headers=Message(); headers[header]='file:///must-not-be-opened'
                            response=addinfourl(BytesIO(),headers,request.full_url,code)
                            response.msg='Found'
                            return response
                    opener=build_opener(ProxyHandler({}),RedirectFixture(),links.SafeRedirects())
                    with patch.object(links,'build_opener',return_value=opener):
                        state,detail=links.check_external('https://public.example/')
                    self.assertEqual(state,'error')
                    self.assertIn('Unsafe redirect:',detail)
    def test_external_error_classification(self):
        for code,expected in [(404,'error'),(410,'error'),(403,'unknown'),(429,'unknown'),(503,'unknown')]:
            with patch.object(links,'build_opener') as factory:
                factory.return_value.open.side_effect=HTTPError('https://public.example/',code,'',{},None)
                self.assertEqual(links.check_external('https://public.example/')[0],expected)
    def test_successful_redirect_is_retained(self):
        result=links.SafeRedirects().redirect_request(Request('https://public.example/'),None,302,'Found',{},'https://other.example/download.pdf')
        self.assertEqual(result.full_url,'https://other.example/download.pdf')
if __name__=='__main__': unittest.main()