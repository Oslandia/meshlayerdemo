FILES=\
    metadata.txt

package: ${FILES} $(wildcard *.py)
	rm -rf meshlayerdemo
	mkdir meshlayerdemo
	cp -r $^ meshlayerdemo/
	rm -f meshlayerdemo.zip
	zip -r meshlayerdemo.zip meshlayerdemo
	rm -r meshlayerdemo

install: package
	rm -rf ${HOME}/.qgis2/python/plugins/meshlayerdemo
	unzip -o meshlayerdemo.zip -d ${HOME}/.qgis2/python/plugins

clean:
	find . -name '*.pyc' | xargs rm -f 
	rm -f meshlayerdemo.zip
