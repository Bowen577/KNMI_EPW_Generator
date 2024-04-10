# Weather and Solar

This project automates the collection of weather data from the Dutch KNMI (Koninklijk Nederlands Meteorologisch Instituut) online database and converts the data to EPW files for use in EnergyPlus simulations.

## Prerequisites

Before running the script, ensure that you have the following Python packages installed:

- numpy
- pandas
- pvlib
- urllib
- zipfile

If you don't have these packages, you can install them using pip:

```bash
pip install numpy pandas pvlib urllib zipfile
```

## Installation

To use this project, follow these steps:

1. Clone the repository to your local machine:

```bash
git clone https://gitlab.com/your-repo-url/weather-and-solar.git
```

2. Navigate to the local folder in the command line:

```bash
cd weather-and-solar
```

## Usage

To generate the weather files for a customized year, run the following command:

```bash
python gen_epw.py --download_year=<customized_year>
```

Replace <customized_year> with the year you would like to generate the weather data for. The generated weather files can be found in the 'Weather Files' folder.

## Note

- The ground temperature in generated epw files are refer to NLD_Amsterdam_062400_IWEC standard weather file
- Weather files for Valkenburg, Soesterberg, and Hoofdplaat are temporarily missing due to lack of data

## License

This project is licensed under the terms of the MIT License.
