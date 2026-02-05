# Anycubic Cloud APK 1.1.27 – findings

Source analysée : `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/`

## 1) Domaines / base URLs

Strings (res/values/strings.xml) :
- `dev_base_url = https://office.anycubic.com/p/d/workbench/`
- `release_domain_name_no_http = cloud-platform.anycubicloud.com`
- `test_domain_name = https://cloud-universe-test.anycubic.com`
- `test_domain_name_no_http = cloud-platform-test.anycubicloud.com`
- `app_download_url_en = https://cloud-universe.anycubic.com/download`
- `pre_release_tracking_url = https://cloud-platform.anycubicloud.com/j/pre/buried/`

`ConfigConstants` construit :
- `RELEASE_PHP_BASE_URL = https://cloud-platform.anycubicloud.com/p/p`
- `TEST_PHP_BASE_URL = https://cloud-universe-test.anycubic.com/p/t`
- `RELEASE_WEB_BASE_URL = https://cloud-platform.anycubicloud.com/w/p`
- `TEST_WEB_BASE_URL = https://cloud-universe-test.anycubic.com/w/t`
- `DEV_BASE_URL = https://office.anycubic.com/p/d/workbench/`
- `RELEASE_WORKBENCH_BASE_URL = RELEASE_PHP_BASE_URL + "/workbench/"`
- `TEST_WORKBENCH_BASE_URL = TEST_PHP_BASE_URL + "/workbench/"`

Choix d’environnement :
- `Le/b.p()` renvoie `DEV_BASE_URL` si env=DEV, `TEST_WORKBENCH_BASE_URL` si env=TEST, sinon `RELEASE_WORKBENCH_BASE_URL`.

Fichiers :
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/values/strings.xml`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/common/constant/ConfigConstants.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/e/b.smali`

## 2) Chaîne vidéo / streaming

Signal vidéo :
-- `BaseMqttHandleActivity` route l’event `EventMessage.key == 0x3e9` vers `onMqttPrintVideoCaptureEvent(PeerCredentials)`.
-- `FDMTaskDetailsActivity` et `LCDTaskDetailsActivity` enregistrent un `ReceivedMqttMsgEventParamBean` avec :
  - `eventMessageKey = 0x3e9`
  - `deviceId = PrintProjectV2Response.key`
  - `targetClazz = PeerCredentials`

Traitement d’event vidéo :
- `onMqttPrintVideoCaptureEvent` vérifie `deviceId` puis traite :
-- `action = "stopCapture"` → affiche erreur “video_stopCapture”
  - `state = initSuccess` → `ACPeerVideoView.createConnection(PeerCredentialsDataBean)`
  - `state = pushStopped` → `ACPeerVideoView.disconnect()`
  - `state = initFailed / pushFailed / agoraFailed` → erreur + code

Credentials :
- `PeerVideoResponse.getToken()` renvoie `PeerCredentialsDataBean` (AWS region/accessKey/secret/sessionToken + agora_error_code).
- `PeerVideoResponse` contient aussi un `ShengwangTokenBean` (token Agora/Shengwang).

Libs vidéo :
- AWS Kinesis Video + signaling (`PeerConfiguration`) utilise `PeerCredentialsDataBean`.
- Agora/Shengwang présents (`PeerVideoResponse.shengwang`).

Fichiers :
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/common/base/BaseMqttHandleActivity.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/common/base/BaseMqttHandleFragment.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/common/ext/r.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/FDMTaskDetailsActivity.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/LCDTaskDetailsActivity.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/FDMTaskDetailsActivity$m.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/ac/cloud/publicbean/main/data/response/PeerVideoResponse.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/ac/cloud/publicbean/main/data/response/PeerCredentialsDataBean.smali`
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/peer/PeerConfiguration.smali`

## 4) Endpoints vidéo (Retrofit)

Service `PeerVideoService` :
- `POST api/work/operation/sendOrder` (fields: `order_id`, `printer_id`) → `PeerVideoResponse`
- `POST api/user/cloud_storage/getTcCosTempToken` (fields: `category`, `type`) → `UploadTokenBean`

Fichier :
- `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/PeerVideoService.smali`

## 5) Routes Retrofit (hors libs tierces)

Format : `METHOD  PATH  CLASS  FILE`

GET api/makeronline/common/request  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/makeronline/home/getTags  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/makeronline/home/getTrending  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/makeronline/profile/followList  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/makeronline/profile/getPersonalInfo  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/makeronline/profile/getPersonalMold  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/makeronline/profile/transfersRule  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/makeronline/themes/getThemes  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/portal/index/reason  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/user/profile/check_userclose  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
GET api/user/profile/userInfo  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
GET api/user/profile/userclose  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
GET api/user/upload/getSupportFileExtension  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/v2/Printer/status  Lw/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/w/a.smali
GET api/v2/model/getUserSearchHistory  Ln/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/n/a.smali
GET api/v2/printer/all  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/v2/printer/functions  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/v2/printer/info  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/v2/printer/readQuickStartUrl  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/v2/printer/sliceConfig  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
GET api/v2/printer/tool  Lw/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/w/a.smali
GET api/v2/project/autoOperation  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
GET api/v2/project/info  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
GET api/v2/project/monitor  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
GET api/v2/project/printHistory  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/v3/im/getUserAndSig  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
GET api/v3/message/getMessageSwitchStatus  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
GET api/v3/model/getHotSearchTerm  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/v3/model/trending  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
GET api/v3/work_project/getErrorList  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
GET api/v4/message/getMessageCount  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
GET api/v4/model/getCategoryAndOrderRule  Ln/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/n/a.smali
GET api/work/gcode/info  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/gcode/infoFdm  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/index/files  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/index/getMqttFilter  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/index/getPlateInfo  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/index/getWifiInfo  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/index/index  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/index/printerAddHelp  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/printer/getPrinters  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/printer/printersStatus  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/printer/unsetprinters  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/printer/update_version  Lz/c;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/c.smali
GET api/work/project/getProjects  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
GET api/work/project/info  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
GET api/work/project/report  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
GET api/work/project/unsetprojects  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
GET api/work/slice/getSliceFilamentByMachineType  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
GET api/work/slicetemplate/gettemplatesV2  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
POST api/makeronline/common/request  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
POST api/makeronline/profile/followCancel  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
POST api/makeronline/profile/followOne  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
POST api/makeronline/profile/integralTransfer  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
POST api/makeronline/report/reportMold  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
POST api/makeronline/report/reportReason  Lm/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/m/a.smali
POST api/portal/index/feedback_mobile  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/portal/index/getFeedbackInfo  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/portal/index/getFeedbackList  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/portal/index/get_version/  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/portal/machine_material/getColorGroupListById  Lz/c;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/c.smali
POST api/portal/machine_material/getMaterialDryList  Lz/c;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/c.smali
POST api/portal/machine_material/getMaterialList  Lz/c;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/c.smali
POST api/user/captcha/canSendSms  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/captcha/canSendSms  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/captcha/userExists  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/cloud_storage/getTcCosTempToken  Lcom/anycubic/lib/video/PeerVideoService;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/PeerVideoService.smali
POST api/user/profile/bindingMobile  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/profile/changePassword  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/profile/checkPasswordBeforeBind  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/profile/getRandomNickname  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/profile/userInfo  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/public/login  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/public/logout  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/public/passwordReset  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/public/passwordResetCheck  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/public/register  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/user/public/scanLogin  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/public/scanOperation  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/verification_code/newSend  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/user/verification_code/newSend  Lx/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/x/a.smali
POST api/v2/cloud_storage/getPreSignUrlArrWithName  Lj/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/j/a.smali
POST api/v2/cloud_storage/lockStorageSpace  Lj/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/j/a.smali
POST api/v2/cloud_storage/unlockStorageSpace  Lj/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/j/a.smali
POST api/v2/device/getPrinterOptions  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
POST api/v2/device_function/funConfig  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/v2/message/getMessages  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
POST api/v2/message/setReadById  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
POST api/v2/model/clearSearchHistory  Ln/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/n/a.smali
POST api/v2/model/getSliceListById  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/v2/model/isSliceFile  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
POST api/v2/model/isSliceFile  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/v2/model/smartLink  Ln/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/n/a.smali
POST api/v2/printer/getMultiColorBoxInfo  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
POST api/v2/printer/getMultiColorBoxInfo  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/v2/printer/update_multi_color_box_version  Lz/c;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/c.smali
POST api/v2/profile/newUploadFile  Lj/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/j/a.smali
POST api/v2/store/info  Lh0/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes5/h0/b.smali
POST api/v2/translate/getInfoByTypeFunctionId  Lw/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/w/a.smali
POST api/v3/message/hasNewMessage  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
POST api/v3/message/setMessageSwitchStatus  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
POST api/v3/message/setRead  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
POST api/v3/message/setReadByType  Lac/cloud/message/api/b;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/message/api/b.smali
POST api/v3/model/getSliceFileCount  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/v3/printer/getPrinterFileDetails  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
POST api/v3/work_project/feedback  Lf0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/f0/a.smali
POST api/v4/model/searchModel  Ln/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/n/a.smali
POST api/work/index/delFiles  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/work/index/getUserStore  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/work/index/renameFile  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/work/operation/sendOrder  Lcom/anycubic/lib/video/PeerVideoService;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/PeerVideoService.smali
POST api/work/operation/sendOrder  Lcom/cloud/mqttservice/apiservice/CommandApiService;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/cloud/mqttservice/apiservice/CommandApiService.smali
POST api/work/printer/Info  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/work/slice/checkSliceParam  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
POST api/work/slicetemplate/update  Lc0/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/c0/a.smali
POST api/work/work/addprinter  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST api/work/work/checkConfigId  Lz/a;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/z/a.smali
POST buried/report  Lac/cloud/common/tracking/TrackingApiService;  /home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/common/tracking/TrackingApiService.smali

## 6) Remarques

- Aucun endpoint explicite `api/user/profile/getVideoUrl` ou `stopVideo` n’est présent dans l’APK 1.1.27. L’arrêt de capture passe par MQTT (`action = stopCapture`).
- La logique vidéo combine `PeerVideoService` (credentials AWS + token Agora/Shengwang).
