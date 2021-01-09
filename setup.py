from distutils.core import setup
setup(
  name = 'wiserHeatAPIv2',
  packages = ['wiserHeatAPIv2'],
  version = '0.0.1',
  license='MIT',
  description = 'A simple API for controlling the Drayton Wiser Heating system',
  author = 'Mark Parker',
  author_email = 'msparker@sky.com',
  url = 'https://github.com/msp1974/wiserheatapiv2',
  download_url = 'https://github.com/msp1974/wiserheatapiv2/archive/v_01.tar.gz',    # I explain this later on
  keywords = ['Wiser', 'Heating', 'V2', 'API'],
  install_requires=[],
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.8',
  ],
)
