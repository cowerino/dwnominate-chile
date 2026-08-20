! R compatibility shims for standalone compilation
! Replaces R's intpr, realpr, rexit with standard Fortran I/O

subroutine intpr(label, nchar, data, ndata)
  implicit none
  character(len=*), intent(in) :: label
  integer, intent(in) :: nchar, ndata
  integer, intent(in) :: data(*)
  integer :: i

  if (ndata > 0) then
    write(*, '(A,A)', advance='no') '  ', trim(label)
    do i = 1, ndata
      write(*, '(A,I0)', advance='no') ' ', data(i)
    enddo
    write(*,*)
  else
    write(*, '(A,A)') '  ', trim(label)
  endif
end subroutine intpr

subroutine realpr(label, nchar, data, ndata)
  implicit none
  character(len=*), intent(in) :: label
  integer, intent(in) :: nchar, ndata
  real, intent(in) :: data(*)
  integer :: i

  if (len_trim(label) > 0) then
    write(*, '(A,A)', advance='no') '  ', trim(label)
  endif
  do i = 1, ndata
    write(*, '(A,F10.4)', advance='no') ' ', data(i)
  enddo
  write(*,*)
end subroutine realpr

subroutine dblepr(label, nchar, data, ndata)
  implicit none
  character(len=*), intent(in) :: label
  integer, intent(in) :: nchar, ndata
  double precision, intent(in) :: data(*)
  integer :: i

  if (len_trim(label) > 0) then
    write(*, '(A,A)', advance='no') '  ', trim(label)
  endif
  do i = 1, ndata
    write(*, '(A,F12.6)', advance='no') ' ', data(i)
  enddo
  write(*,*)
end subroutine dblepr

subroutine rexit(msg)
  implicit none
  character(len=*), intent(in) :: msg
  write(*, '(A,A)') 'FATAL: ', trim(msg)
  stop 1
end subroutine rexit
