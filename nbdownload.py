import urllib.request
import urllib.error
import os
import io
import sys
from PIL import Image
from fpdf import FPDF


class Book:


    def __init__(self, book_id, length=None):
        self.id = str(book_id)
        self.length = length
        self.rows = -1
        self.cols = -1
        self.img_size = [0, 0]
        self.params = {"book_id": str(book_id), "page_nr": "1", "long_page_nr": "0001", "col": "0", "row": "0"}
        self.retry = 2 # Establish a counter for download error retries
        self.path = book_id + "_temp_image_folder\\"
        self.fullpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.path)
        if not os.path.exists(self.fullpath):
            os.mkdir(self.path)
        self.url_template = "https://www.nb.no/services/image/resolver?url_ver=geneza&urn=URN:NBN:no-nb_digibok_{book_id}_{long_page_nr}&maxLevel=5&level=5&col={col}&row={row}&resX=9999&resY=9999&tileWidth=1024&tileHeight=1024&pg_id={page_nr}"
        self._find_rows_cols_and_img_size()

    def download_page(self, page_nr, retry):

        # Get the partial images and stich the image together
        page = Image.new("RGB", tuple(self.img_size), "white") # Any unused space in the image will be white
        x_offset = 0
        y_offset = 0
        for row in range(self.rows):
            col = 0
            while col < self.cols:
                self.update_params(page_nr, col, row)
                try:
                    response = (urllib.request.urlopen(self.url_template.format(**self.params))).read()
                except urllib.error.HTTPError:
                    print("Download Error: Is the page number, column or row too high?")
                    print("Tried to access "+self.url_template.format(**self.params))
                    # Check retry counter, prevents program from hanging if the download error isn't overcome with three retries
                    if self.retry >= 0:
                        print("Retrying.... "+str(self.retry)+ " tries remaining.")
                        self.retry -= 1
                        col -= 1
                    else:
                        print("All retries failed")
                except:
                    print("Other error")
                    exit()
                else:
                    partial_page = Image.open(io.BytesIO(response))
                    page.paste(partial_page, (x_offset, y_offset))
                    x_offset+=partial_page.width

                # Finished this row
                if col == self.cols-1:
                    x_offset = 0
                    y_offset += partial_page.height
                col += 1

        page.save(self.id+"_temp_image_folder\\"+str(page_nr)+".jpg")

    def find_book_length(self):
        # Search semi-linearly for the books length
        delta = 100
        j = 100
        while True:
            self.update_params(j,0,0)
            try:
                urllib.request.urlopen(self.url_template.format(**self.params))

            except urllib.error.HTTPError:
                # Too far
                if delta == 1:
                    return j-1
                j -= delta
                delta = int(delta / 10)
                j += delta
            else:
                j += delta


    def download_book(self):
        # Sets PDF size - Might want to make a variable based on image size....
        pdf = FPDF(format="Letter")
        if self.length is None:
            print("Length not specified, calculating book length")
            self.length = self.find_book_length()
            print("Book length found: ",self.length)

        print("Downloading book", self.id)
        retry = 2

        # Front Cover:
        self.download_page("C1", retry)
        self.retry = 2
        pdf.add_page()
        pdf.image(self.id+"_temp_image_folder\\" + "C1" + ".jpg", 0, 0, 210, 297)

        for page in range(1, self.length+1):
            self.download_page(page, retry)
            print("Page", page, "download complete")
            self.retry = 2

        for page in range(1, self.length+1):
            pdf.add_page()
            pdf.image(self.id+"_temp_image_folder\\" + str(page) + ".jpg", 0, 0, 210, 297)

        # Back Cover
        self.download_page("C3", retry)
        pdf.add_page()
        pdf.image(self.id + "_temp_image_folder\\" + "C3" + ".jpg", 0, 0, 210, 297)

        pdf.output(self.id + ".pdf")
        print("Pdf saved of book",self.id)

    def get_file_name(self,col,row):
        return self.id+"_"+self.params["long_page_nr"]+"_"+str(row)+"_"+str(col)

    def update_params(self, page_nr = None, col = None, row = None):
        if page_nr is not None:
            page_nr = str(page_nr)
            self.params["page_nr"] = page_nr
            if page_nr.isdigit():
                self.params["long_page_nr"] = page_nr.rjust(4, "0")
            else:
                self.params["long_page_nr"] = page_nr

        if col is not None :
            self.params["col"] = str(col)

        if row is not None:
            self.params["row"] = str(row)

    def _find_rows_cols_and_img_size(self):
        # Rows
        while True:
            self.rows += 1
            self.update_params(1, 0, self.rows)
            try:
                response = (urllib.request.urlopen(self.url_template.format(**self.params))).read()
                image = Image.open(io.BytesIO(response))
                self.img_size[1] += image.height
            except urllib.error.HTTPError:
                break
        #Cols
        while True:
            self.cols += 1
            self.update_params(1, self.cols,0)
            try:
                response = urllib.request.urlopen(self.url_template.format(**self.params)).read()
                image = Image.open(io.BytesIO(response))
                self.img_size[0] += image.width
            except urllib.error.HTTPError:
                break

def main():
# Request book_id from console arguments
  book_id = sys.argv[1]
  b = Book(book_id)
  b.download_book()

if __name__ == "__main__":
    main()
