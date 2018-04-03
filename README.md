# qnap_cloudbackup_test
Python source code for automating basic function test for QNAP CloudBackup applications

Cloud services:
- Dropbox
- Google Drive
- Amazon
- OneDrive
- Box.com
- Yandex
- Hubic

The automation script covers the following test:
1. Folders and files creation
2. Folders and files move operation
3. Folders and files renaming
4. Folders and files deletion
5. Folders depth test (10 levels)
6. Different file types (documents, music, videos, images, etc...)
7. Folder and files with long names (over than 128 characters long)
8. Files with special characters name (!@#$%...)
9. Files with multi-byte charactesr name 
10. Huge amount of small files (10,000 files with size 10 Bytes)
11. Huge amount of files moving operation (move 1,000 files)
12. Huge file size (1 GB)

The purpose of the test is to automate above cases > automatically check the results by comparing the Cloud drive and NAS storage after each backup / restore operation is complete > generate HTML report test.
