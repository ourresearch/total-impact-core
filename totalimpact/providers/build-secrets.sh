# Sets up credentials file for sharing; run every time creds.ini changes.
# Creates an encrypted version of creds.ini for storing in version control.
# If creds.ini doesn't exist, this creates it from the encrypted file.
# Also makes a sample config file.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f ${DIR}/secrets.py ] # the creds file exists
then
    # store an encrypted version
    rm ${DIR}/secrets.des3
    openssl des3 -salt -in ${DIR}/secrets.py -out ${DIR}/secrets.des3

    # create a sample config file
    sed 's/^\(.*\) =.*/\1 = <\1>/g' < ${DIR}/secrets.py > ${DIR}/secrets.py.sample
else
    # decrypt the encrypted creds.ini
    openssl des3 -d -salt -in ${DIR}/secrets.des3 -out ${DIR}/secrets.py
fi