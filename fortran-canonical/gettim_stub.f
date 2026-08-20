C  Stub for MS Fortran GETTIM intrinsic (hour,minute,second,hundredths)
C  Cosmetic: used only for elapsed-time reporting. Real wall clock.
      SUBROUTINE GETTIM(IH,IM,IS,ICS)
      INTEGER*2 IH,IM,IS,ICS
      INTEGER VALS(8)
      CALL DATE_AND_TIME(VALUES=VALS)
      IH =INT(VALS(5),2)
      IM =INT(VALS(6),2)
      IS =INT(VALS(7),2)
      ICS=INT(VALS(8)/10,2)
      RETURN
      END
