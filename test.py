# -*- coding: UTF-8 -*-
import win32com.client

fr = win32com.client.Dispatch('Addin.DRvFR')
error_print_check_code = fr.ResultCode
error_decription = fr.ResultCodeDescription
print(error_print_check_code, error_decription)
fr.GetECRStatus()
er_ecr = fr.ECRMode
er_ecr_desc = fr.ECRModeDescription
print(er_ecr, er_ecr_desc)
er_ecr_adv = fr.ECRAdvancedMode
er_ecr_desc_adv = fr.ECRAdvancedModeDescription
print(er_ecr_adv, er_ecr_desc_adv)
