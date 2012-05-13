# Sets up credentials file for sharing; run every time creds.ini changes.
# Creates an encrypted version of creds.ini for storing in version control.
# If creds.ini doesn't exist, this creates it from the encrypted file.
# Also makes a sample config file.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f ${DIR}/creds.cfg ] # the creds file exists
then
    # store an encrypted version
    rm ${DIR}/creds.des3
    openssl des3 -salt -in ${DIR}/creds.cfg -out ${DIR}/creds.des3

    # create a sample config file
    sed 's/^\(.*\) =.*/\1 = <\1>/g' < ${DIR}/creds.cfg > ${DIR}/creds.cfg.sample
else
    # decrypt the encrypted creds.ini
    openssl des3 -d -salt -in ${DIR}/creds.des3 -out ${DIR}/creds.cfg
fi