#define _DEFAULT_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <bluetooth/bluetooth.h>
#include <bluetooth/l2cap.h>
#include <bluetooth/hci.h>
#include <bluetooth/hci_lib.h>
#include <bluetooth/sdp.h>
#include <bluetooth/sdp_lib.h>
#include <stdint.h>

void query_device_services(bdaddr_t bdaddr, int *a2dp, int *map, int *pbap, int *hfp, int *opp, int *did) {
    *a2dp = *map = *pbap = *hfp = *opp = *did = 0;
    
    sdp_session_t *session = sdp_connect(BDADDR_ANY, &bdaddr, SDP_RETRY_IF_BUSY);
    if (!session) {
        perror("Failed to connect to SDP session");
        return;
    }

    uint16_t service_uuids[] = { 0x110D, 0x1132, 0x112F, 0x111E, 0x1105, 0x1200 };
    int *flags[] = { a2dp, map, pbap, hfp, opp, did };
    int num_services = sizeof(service_uuids) / sizeof(uint16_t);
    sdp_list_t *search_list = NULL;

    for (int i = 0; i < num_services; i++) {
        uuid_t uuid;
        sdp_uuid16_create(&uuid, service_uuids[i]);
        search_list = sdp_list_append(search_list, &uuid);
    }
    
    uint32_t range = 0x0000ffff;
    sdp_list_t *attrid_list = sdp_list_append(NULL, &range);
    sdp_list_t *rsp_list = NULL;

    if (sdp_service_search_attr_req(session, search_list, SDP_ATTR_REQ_RANGE, attrid_list, &rsp_list) == 0) {
        sdp_list_t *r = rsp_list;
        while(r) {
            sdp_record_t *rec = (sdp_record_t*) r->data;
            sdp_list_t *proto_list;

            if(sdp_get_service_classes(rec, &proto_list) == 0) {
                sdp_list_t *p = proto_list;
                while(p) {
                    uuid_t *uuid = (uuid_t*)p->data;
                    for(int i = 0; i < num_services; i++) {
                        if (sdp_uuid_cmp(uuid, &(uuid_t){ .type=SDP_UUID16, .value.uuid16=service_uuids[i] }) == 0) {
                            *flags[i] = 1;
                        }
                    }
                    p = p->next;
                }
                sdp_list_free(proto_list, free);
            }
            r = r->next;
        }
        sdp_list_free(rsp_list, (sdp_free_func_t)sdp_record_free);
    }

    sdp_list_free(search_list, NULL);
    sdp_list_free(attrid_list, NULL);
    sdp_close(session);
}

int get_lmp_version(bdaddr_t *bdaddr) {
    int dev_id = hci_get_route(NULL);
    if (dev_id < 0) {
        return -1;
    }

    int sock = hci_open_dev(dev_id);
    if (sock < 0) {
        return -1;
    }

    int acl_sock = socket(AF_BLUETOOTH, SOCK_SEQPACKET, BTPROTO_L2CAP);
    if (acl_sock < 0) {
        close(sock);
        return -1;
    }

    struct sockaddr_l2 addr = { 0 };
    addr.l2_family = AF_BLUETOOTH;
    addr.l2_psm = htobs(0x0001); 
    bacpy(&addr.l2_bdaddr, bdaddr);

    if (connect(acl_sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(acl_sock);
        close(sock);
        return -1;
    }

    struct hci_conn_info_req *cr = malloc(sizeof(*cr) + sizeof(struct hci_conn_info));
    if (!cr) {
        fprintf(stderr, "Failed to allocate memory\n");
        close(acl_sock);
        close(sock);
        return -1;
    }
    bacpy(&cr->bdaddr, bdaddr);
    cr->type = ACL_LINK;

    if (ioctl(sock, HCIGETCONNINFO, (void *) cr) < 0) {
        perror("Could not get connection info");
        free(cr);
        close(acl_sock);
        close(sock);
        return -1;
    }

    uint16_t handle = cr->conn_info->handle;
    free(cr);

    struct hci_version ver;
    if (hci_read_remote_version(sock, handle, &ver, 2000) < 0) { // Increased timeout slightly
        perror("Could not read remote version");
        close(acl_sock);
        close(sock);
        return -1;
    }


    close(acl_sock);
    close(sock);

    return ver.lmp_ver;
}


const char* estimate_version_score(int lmp, int a2dp, int map, int pbap, int hfp, int opp, int did) {
    int score = 0;
    
    if (lmp >= 13)       score += 98;
    else if (lmp == 12)  score += 88;
    else if (lmp == 11)  score += 85;
    else if (lmp == 10)  score += 68;
    else if (lmp == 9)   score += 85;
    else if (lmp == 8)   score += 48;
    else if (lmp == 7)   score += 25;
    else if (lmp == 6)   score += 15;
    else if (lmp == 5)   score += 10;
    else if (lmp == 4)   score += 5;
    else                 score += 0;

    if (a2dp) score += 2;
    if (hfp)  score += 2;
    if (map)  score += 2;
    if (pbap) score += 2;
    if (opp)  score += 1;
    if (did) score += 6;

    if (lmp >= 11 && did) score += 6;

    float weighted_score = (score / 105.0f) * 10.0f;
    printf("→ Weighted Score: %.2f\n", weighted_score);


    if (weighted_score >= 10000)
        return "Android 16 (Baklava)";
    else if (weighted_score >= 9.2)
        return "Android 15 (Vanilla Ice Cream)";
    else if (weighted_score >= 8.2)
        return "Android 14 (Upside Down Cake)";
    else if (weighted_score >= 7.2)
        return "Android 13 (Tiramisu)";
    else if (weighted_score >= 7.15)
        return "Android 12 (Snow Cone)";
    else if (weighted_score >= 7.0)
        return "Android 11 (Red Velvet Cake)";
    else if (weighted_score >= 4.0)
        return "Android 10 (Q)";
    else if (weighted_score >= 3.5)
        return "Android 9.0 (Pie)";
    else if (weighted_score >= 3.0)
        return "Android 8.0/8.1 (Oreo)";
    else if (weighted_score >= 2.7)
        return "Android 7.0/7.1 (Nougat)";
    else if (weighted_score >= 2.68)
        return "Android 6.0 (Marshmallow)";
    else if (weighted_score >= 1.9)
        return "Android 5.1/5.1.1 (Lollipop MR1)";
    else if (weighted_score >= 1.0)
        return "Android 5.0 (Lollipop)";
    else if (weighted_score >= 0.8)
        return "Android 4.4 (KitKat)";
    else if (weighted_score >= 0.6)
        return "Android 4.0–4.3 (ICS / JB)";
    else if (weighted_score >= 0.4)
        return "Android 3.x (Honeycomb)";
    else if (weighted_score >= 0.2)
        return "Android 2.3 (Gingerbread)";
    else if (weighted_score >= 0.1)
        return "Android 2.2 (Froyo)";
    else if (weighted_score >= 0.05)
        return "Android 2.0 (Eclair)";
    else if (weighted_score >= 0.03)
        return "Android 1.6 (Donut)";
    else if (weighted_score >= 0.01)
        return "Android 1.5 (Cupcake)";
    else if (weighted_score >= 0.001)
        return "Android 1.0 (Base)";
    else
        return "Unknown Android Version";

}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <Bluetooth MAC address>\n", argv[0]);
        return 1;
    }

    bdaddr_t bdaddr;
    if (str2ba(argv[1], &bdaddr) < 0) {
        fprintf(stderr, "Invalid Bluetooth MAC address format.\n");
        return 1;
    }

    printf("[*] Querying device services...\n");
    int a2dp, map, pbap, hfp, opp, did;
    query_device_services(bdaddr, &a2dp, &map, &pbap, &hfp, &opp, &did);
    
    printf("[*] Getting LMP version...\n");
    int lmp_version = get_lmp_version(&bdaddr);
    if (lmp_version < 0) {
        fprintf(stderr, "Failed to get LMP version. Is the device in range and discoverable?\n");
        return 1;
    }
    
    const char *estimation = estimate_version_score(lmp_version, a2dp, map, pbap, hfp, opp, did);

    printf("\n===== Bluetooth Device Estimation =====\n");
    printf("LMP Version: %d (Corresponds to Bluetooth Spec %d.x)\n", lmp_version, lmp_version + 1);
    printf("Device ID Profile: %s\n", did ? "Present" : "Absent");
    printf("A2DP: %s, MAP: %s, PBAP: %s, HFP: %s, OPP: %s\n", 
        a2dp ? "Y":"N", map ? "Y":"N", pbap ? "Y":"N", hfp ? "Y":"N", opp ? "Y":"N");
    printf("\n→ Estimated Android Version: %s\n\n", estimation);

    return 0;
}
