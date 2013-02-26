#!/usr/bin/env sh

# Script to prime the database based on existing metadata and parsets.
# Once the project is complete using fixtures will be more convenient, but
# this enables us to more easily redesign & reinitialize the data while
# developing.

WORKING_DIR=`dirname ${0}`
SCRIPT_DIR=${WORKING_DIR}/scripts
METADATA_DIR=${WORKING_DIR}/metadata
DATA_DIR=${WORKING_DIR}/data

export PYTHONPATH=${WORKING_DIR}${PYTHONPATH:+:${PYTHONPATH}}
export DJANGO_SETTINGS_MODULE="obsdb.settings"

python ${SCRIPT_DIR}/create_stations.py ${METADATA_DIR}/StationInfo.dat
python ${SCRIPT_DIR}/create_survey.py "MSSS LBA" 2.885 9 ${METADATA_DIR}/calibrators.lba.txt ${METADATA_DIR}/grid.lba.txt
python ${SCRIPT_DIR}/create_survey.py "MSSS HBA" 1.21 2 ${METADATA_DIR}/calibrators.hba.txt ${METADATA_DIR}/grid.hba.txt
python ${SCRIPT_DIR}/load_data.py ${DATA_DIR}/parsets
python ${SCRIPT_DIR}/load_data_hba.py ${DATA_DIR}/parsets
python ${SCRIPT_DIR}/mark_as_archived.py ${METADATA_DIR}/archived_data.txt
python ${SCRIPT_DIR}/mark_as_invalid.py ${METADATA_DIR}/invalid.txt
python ${SCRIPT_DIR}/lta.py ${METADATA_DIR}/archived_20130219.csv
python ${SCRIPT_DIR}/lta.py ${METADATA_DIR}/archived_hba_20130219.csv
python ${SCRIPT_DIR}/insert_node_data_list.py ${DATA_DIR}/node_listing/locus*log
