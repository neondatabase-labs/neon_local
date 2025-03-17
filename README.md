# Neon Local

To install it locally, you need:

1. create a `.neon.local` file by running `echo '{}' > .neon.local`
1. ignore this file `echo .neon.local >> .gitignore`
1. define two env variables: `NEON_API_KEY` and `NEON_PROJECT_ID`
1. update your docker-compose.yml like in the example (if you need postgres protocol, choose `neon_local_proxy`; for serverless driver – choose `neon_local_http`)

@todo: change `build` with `image` section

# For docker on Mac

Please change the Virtual Machine Manager. There is a bug with VirtioFS that users 

![How to change the image](img/disc.png)