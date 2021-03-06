from d_parser.d_spider_common import DSpiderCommon
from d_parser.helpers.re_set import Ree
from helpers.url_generator import UrlGenerator


VERSION = 28


# Warn: Don't remove task argument even if not use it (it's break grab and spider crashed)
# Warn: noinspection PyUnusedLocal
class DSpider(DSpiderCommon):
    def __init__(self, thread_number, try_limit=0):
        super().__init__(thread_number, try_limit)

    # fetch categories
    def task_initial(self, grab, task):
        try:
            if self.check_body_errors(grab, task):
                yield self.check_errors(task)
                return

            # catalog
            catalog = grab.doc.select('//div[contains(@class, "content")]//a')

            for link in catalog:
                link = UrlGenerator.get_page_params(self.domain, link.attr('href'), {})
                yield self.do_task('parse_page', link, 90)

        except Exception as e:
            self.process_error(grab, task, e)

        finally:
            self.process_finally(task)

    # parse page pagination
    def task_parse_page(self, grab, task):
        try:
            if self.check_body_errors(grab, task):
                yield self.check_errors(task)
                return

            # sub categories
            sub_cats = grab.doc.select('//ul[@class="catalog-parts"]//a')

            for link in sub_cats:
                link = UrlGenerator.get_page_params(self.domain, link.attr('href'), {})
                yield self.do_task('parse_page', link, 90)

            # items
            items_list = grab.doc.select('//figure[contains(@class, "catalog-item")]//a[@class="name"]')

            for link in items_list:
                link = UrlGenerator.get_page_params(self.domain, link.attr('href'), {})
                yield self.do_task('parse_item', link, 100, last=True)

            # parse next page link
            next_page = grab.doc.select('//div[@class="pages"]//a[contains(text(), "Следующая")]').attr('href', '')

            if next_page:
                next_page = UrlGenerator.get_page_params(self.domain, next_page, {})
                yield self.do_task('parse_page', next_page, 90)

        except Exception as e:
            self.process_error(grab, task, e)

        finally:
            self.process_finally(task)

    # parse single item
    def task_parse_item(self, grab, task):
        try:
            if self.check_body_errors(grab, task):
                yield self.check_errors(task)
                return

            # common block with info
            product_info = grab.doc.select('//div[@class="product-information"]')

            # parse fields
            # A = name
            product_name = grab.doc.select('//h1').text()

            # B = count (quantity)
            # C = status (delivery)
            product_count_string = product_info.select('.p[@class="product-available green"]').text('')

            if product_count_string:
                product_count = '-1'
                product_status = '0'

            else:
                self.log.warning(task, f'Unknown count status {product_count_string} skip...')
                return

            # D = unit (measure) [const!]
            product_unit = 'ед.'

            # E = price
            product_price_raw = product_info.select('.//div[@class="item_current_price"]').text('')
            product_price_raw = Ree.extract_float.match(product_price_raw)

            if product_price_raw:
                product_price = product_price_raw.groupdict()['float']

            else:
                self.log.warning(task, f'Unknown price status {product_price_raw}, skip...')
                return

            if product_price == '0':
                product_price = '-1'

            table = product_info.select('.//table[@class="prop-list"]//tr')

            product_vendor_code = ''
            product_vendor = ''

            for row in table:
                key = row.select('./td[1]').text('')
                value = row.select('./td[2]').text('')

                # G = vendor (manufacture)
                if 'Производитель' in key:
                    product_vendor = value
                    continue

                # F = vendor code (sku)
                if 'Артикул' in key:
                    product_vendor_code = value.strip(' .')
                    continue

            # H = photo url
            product_photo_url_raw = product_info.select('.//a[@id="pos-big-photo"]').attr('href', '')

            if product_photo_url_raw:
                product_photo_url = UrlGenerator.get_page_params(self.domain, product_photo_url_raw, {})
            else:
                product_photo_url = ''

            # I = description (properties)
            product_description = {'Описание': product_info.select('.//div[@id="detail-text-content"]').text('')}

            # save
            o = {
                'name': product_name,
                'quantity': product_count,
                'delivery': product_status,
                'measure': product_unit,
                'price': product_price,
                'sku': product_vendor_code,
                'manufacture': product_vendor,
                'photo': product_photo_url,
                'properties': product_description
            }

            self.log.info(task, 'Add: {}'.format(o))

            self.result.append({
                'name': product_name,
                'quantity': product_count,
                'delivery': product_status,
                'measure': product_unit,
                'price': product_price,
                'sku': product_vendor_code,
                'manufacture': product_vendor,
                'photo': product_photo_url,
                'properties': product_description
            })

        except Exception as e:
            self.process_error(grab, task, e)

        finally:
            self.process_finally(task, last=True)
