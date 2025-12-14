# Smart Trash Can Project

Hi everyone this project is:

Streaming data from an image sensor/device to server to detect waste vs recyclable objects classification and return back to the user an answer

Camera -> Raspberry Pi -> ETL Application in Raspberry PI will capture images and send JSON request Raspberry Pi with image/image metadata to local webserver-> Local Web Server will perform validations, transformations,  make ML prediction, insert into master data tables, and return prediction back to Raspberry Pi -> PI will alert user of object classification
