! Standalone main program for DW-NOMINATE Fortran
! Reads CSV vote matrices and calls dwnom() subroutine directly
! Replaces the R wrapper for clean scientific comparison against C++
!
! Usage: dwnominate_fortran <input_dir> <output_dir> <niter> <model>

program dwnominate_standalone
  implicit none

  ! Parameters
  integer, parameter :: MAX_LEGS = 1000
  integer, parameter :: MAX_RCS = 5000
  integer, parameter :: MAX_DIM = 2

  ! NOMSTARTIN: [NS, NMODEL, NFIRST, NLAST, IHAPPY1, IHAPPY2]
  integer :: NOMSTARTIN(6)

  ! Input arrays
  double precision, allocatable :: WEIGHTSIN(:)
  double precision, allocatable :: DYNIN(:,:), ZMIDIN(:,:)
  double precision, allocatable :: XDATAIN(:,:)
  integer, allocatable :: ICONGIN(:), MCONGIN(:,:)
  integer, allocatable :: NCONGIN(:), ID1IN(:)
  integer, allocatable :: RCVOTE1IN(:,:), RCVOTE9IN(:,:)
  integer, allocatable :: RCVOTET1IN(:,:), RCVOTET9IN(:,:)

  ! Output arrays
  double precision, allocatable :: XDATAOUT(:,:)
  double precision, allocatable :: SDX1OUT(:), SDX2OUT(:)
  double precision, allocatable :: VARX1OUT(:), VARX2OUT(:)
  double precision, allocatable :: XBIGLOGOUT(:,:)
  integer, allocatable :: KBIGLOGOUT(:,:)
  double precision, allocatable :: GMPAOUT(:), GMPBOUT(:)
  double precision, allocatable :: DYNOUT(:,:), ZMIDOUT(:,:)
  double precision, allocatable :: WEIGHTSOUT(:)

  ! Local variables
  integer :: NS, NMODEL, NFIRST, NLAST, NITER
  integer :: num_periods, total_legs, total_rcs
  integer :: i, j, p, rc_offset, leg_offset
  integer :: num_legs_in_period, num_rcs_in_period
  integer :: vote_code
  character(len=512) :: input_dir, output_dir, fname
  character(len=512) :: arg
  character(len=65536) :: line
  integer :: argc, ios, unit_num

  ! Timing
  real :: start_time, end_time

  ! Defaults
  input_dir = 'test_single'
  output_dir = 'comparison/fortran_niter1'
  NITER = 1
  NS = 2
  NMODEL = 0

  ! Parse command line arguments
  argc = command_argument_count()
  if (argc >= 1) call get_command_argument(1, input_dir)
  if (argc >= 2) call get_command_argument(2, output_dir)
  if (argc >= 3) then
    call get_command_argument(3, arg)
    read(arg, *) NITER
  endif
  if (argc >= 4) then
    call get_command_argument(4, arg)
    read(arg, *) NMODEL
  endif

  write(*,*) '============================================'
  write(*,*) '  DW-NOMINATE Fortran Standalone'
  write(*,*) '============================================'
  write(*,*) '  Input:  ', trim(input_dir)
  write(*,*) '  Output: ', trim(output_dir)
  write(*,*) '  Iterations: ', NITER
  write(*,*) '  Model: ', NMODEL
  write(*,*) ''

  call cpu_time(start_time)

  ! Step 1: Detect number of periods by counting votes_matrix_p*.csv files
  block
    logical :: fexists
    num_periods = 0
    do i = 1, 100
      write(fname, '(A,A,I0,A)') trim(input_dir), '/votes_matrix_p', i, '.csv'
      inquire(file=trim(fname), exist=fexists)
      if (fexists) then
        num_periods = i
      else
        exit
      endif
    enddo
  end block
  write(*,*) '  Detected periods: ', num_periods

  if (num_periods == 0) then
    write(*,*) 'ERROR: No vote matrix files found in ', trim(input_dir)
    stop 1
  endif

  ! Step 2: Read vote matrices and count dimensions
  ! First pass: count legislators and roll calls per period
  call count_data(input_dir, num_periods, total_legs, total_rcs)

  write(*,*) '  Total legislators: ', total_legs
  write(*,*) '  Total roll calls: ', total_rcs

  ! Step 3: Allocate arrays
  NFIRST = 1
  NLAST = num_periods

  allocate(WEIGHTSIN(NS + 1))
  allocate(DYNIN(total_rcs, NS))
  allocate(ZMIDIN(total_rcs, NS))
  allocate(ICONGIN(total_rcs))
  allocate(MCONGIN(num_periods, 3))
  allocate(NCONGIN(total_legs))
  allocate(ID1IN(total_legs))
  allocate(XDATAIN(total_legs, NS))
  allocate(RCVOTE1IN(total_legs, total_rcs))
  allocate(RCVOTE9IN(total_legs, total_rcs))
  allocate(RCVOTET1IN(total_rcs, total_legs))
  allocate(RCVOTET9IN(total_rcs, total_legs))

  allocate(XDATAOUT(total_legs, NS))
  allocate(SDX1OUT(total_legs))
  allocate(SDX2OUT(total_legs))
  allocate(VARX1OUT(total_legs))
  allocate(VARX2OUT(total_legs))
  allocate(XBIGLOGOUT(total_legs, 2))
  allocate(KBIGLOGOUT(total_legs, 4))
  allocate(GMPAOUT(total_legs))
  allocate(GMPBOUT(total_legs))
  allocate(DYNOUT(total_rcs, NS))
  allocate(ZMIDOUT(total_rcs, NS))
  allocate(WEIGHTSOUT(NS + 1))

  ! Step 4: Initialize
  WEIGHTSIN(1) = 1.0d0    ! W1
  WEIGHTSIN(2) = 0.3463d0 ! W2
  WEIGHTSIN(3) = 5.9539d0 ! Beta

  DYNIN = 0.3d0   ! Default spread
  ZMIDIN = 0.0d0  ! Default midpoints

  NOMSTARTIN(1) = NS
  NOMSTARTIN(2) = NMODEL
  NOMSTARTIN(3) = NFIRST
  NOMSTARTIN(4) = NLAST
  NOMSTARTIN(5) = 1       ! IHAPPY1
  NOMSTARTIN(6) = NITER   ! IHAPPY2

  ! Step 5: Load data
  call load_data(input_dir, num_periods, total_legs, total_rcs, NS, &
                 RCVOTE1IN, RCVOTE9IN, RCVOTET1IN, RCVOTET9IN, &
                 ICONGIN, NCONGIN, ID1IN, XDATAIN, MCONGIN)

  write(*,*) ''
  write(*,*) '  Running DW-NOMINATE...'

  ! Step 6: Call dwnom
  call dwnom(NOMSTARTIN, WEIGHTSIN, total_rcs, ICONGIN, DYNIN, &
             ZMIDIN, MCONGIN, total_rcs, total_legs, RCVOTET1IN, RCVOTET9IN, &
             total_legs, NCONGIN, ID1IN, XDATAIN, total_legs, total_rcs, &
             RCVOTE1IN, RCVOTE9IN, XDATAOUT, SDX1OUT, SDX2OUT, VARX1OUT, &
             VARX2OUT, XBIGLOGOUT, KBIGLOGOUT, GMPAOUT, GMPBOUT, DYNOUT, &
             ZMIDOUT, WEIGHTSOUT)

  call cpu_time(end_time)

  ! Step 7: Export results
  write(*,*) ''
  write(*,*) '  Results:'
  write(*,'(A,F12.4)') '    W2: ', WEIGHTSOUT(2)
  write(*,'(A,F12.4)') '    Beta: ', WEIGHTSOUT(NS+1)
  write(*,'(A,F8.1,A)') '    Time: ', end_time - start_time, 's'

  call export_results(output_dir, total_legs, total_rcs, NS, num_periods, &
                      XDATAOUT, ZMIDOUT, DYNOUT, WEIGHTSOUT, &
                      ID1IN, NCONGIN, NITER)

  write(*,*) ''
  write(*,*) '  Done.'

contains

  subroutine count_data(dir, nper, tot_legs, tot_rcs)
    character(len=*), intent(in) :: dir
    integer, intent(in) :: nper
    integer, intent(out) :: tot_legs, tot_rcs
    character(len=512) :: fn
    character(len=65536) :: line
    integer :: p, nrc, nleg, ios, u
    integer :: first_leg_count

    tot_rcs = 0
    tot_legs = 0
    first_leg_count = 0

    do p = 1, nper
      write(fn, '(A,A,I0,A)') trim(dir), '/votes_matrix_p', p, '.csv'
      u = 20 + p
      open(unit=u, file=trim(fn), status='old', action='read', iostat=ios)
      if (ios /= 0) then
        write(*,*) 'ERROR: Cannot open ', trim(fn)
        stop 1
      endif

      ! Count columns from header (= number of roll calls)
      read(u, '(A)') line
      nrc = count_commas(line)  ! number of commas = number of roll calls

      ! Count data rows (= number of legislators)
      nleg = 0
      do
        read(u, '(A)', iostat=ios) line
        if (ios /= 0) exit
        if (len_trim(line) > 0) nleg = nleg + 1
      enddo
      close(u)

      if (p == 1) first_leg_count = nleg
      tot_rcs = tot_rcs + nrc

      write(*,'(A,I2,A,I4,A,I6)') '    Period ', p, ': ', nleg, ' legislators x ', nrc, ' roll calls'
    enddo

    ! All periods share the same legislator roster (unified list)
    tot_legs = first_leg_count
  end subroutine

  integer function count_commas(str)
    character(len=*), intent(in) :: str
    integer :: i
    count_commas = 0
    do i = 1, len_trim(str)
      if (str(i:i) == ',') count_commas = count_commas + 1
    enddo
  end function

  subroutine load_data(dir, nper, nlegs, nrcs, ndim, &
                       rv1, rv9, rvt1, rvt9, &
                       icong, ncong, id1, xdata, mcong)
    character(len=*), intent(in) :: dir
    integer, intent(in) :: nper, nlegs, nrcs, ndim
    integer, intent(out) :: rv1(nlegs, nrcs), rv9(nlegs, nrcs)
    integer, intent(out) :: rvt1(nrcs, nlegs), rvt9(nrcs, nlegs)
    integer, intent(out) :: icong(nrcs), ncong(nlegs), id1(nlegs)
    double precision, intent(out) :: xdata(nlegs, ndim)
    integer, intent(out) :: mcong(nper, 3)

    character(len=512) :: fn
    character(len=65536) :: line
    character(len=20) :: token
    integer :: p, i, j, u, ios, rc_off, vote, leg_id
    integer :: nrc_period, comma_pos, start_pos
    integer, allocatable :: period_votes(:,:)
    integer, allocatable :: leg_ids(:)
    double precision :: frac

    ! Initialize
    rv1 = 0
    rv9 = 0
    rvt1 = 0
    rvt9 = 0
    xdata = 0.0d0

    rc_off = 0

    do p = 1, nper
      write(fn, '(A,A,I0,A)') trim(dir), '/votes_matrix_p', p, '.csv'
      u = 20 + p
      open(unit=u, file=trim(fn), status='old', action='read', iostat=ios)

      ! Skip header
      read(u, '(A)') line
      nrc_period = count_commas(line)

      ! Read each legislator row
      do i = 1, nlegs
        read(u, '(A)', iostat=ios) line
        if (ios /= 0) exit

        ! Parse: first field is legislator_id, rest are votes
        start_pos = 1
        ! Skip legislator ID field
        comma_pos = index(line(start_pos:), ',')
        if (p == 1) then
          ! Read leg ID from first period
          read(line(1:comma_pos-1), *, iostat=ios) leg_id
          id1(i) = leg_id
        endif
        start_pos = comma_pos + 1

        ! Parse vote fields
        do j = 1, nrc_period
          comma_pos = index(line(start_pos:), ',')
          if (comma_pos == 0) then
            token = line(start_pos:)
          else
            token = line(start_pos:start_pos+comma_pos-2)
          endif

          read(token, *, iostat=ios) vote
          if (ios /= 0) vote = 9

          ! Translate: 1=Yea, 6=Nay, 9=Missing
          if (vote == 1) then
            rv1(i, rc_off + j) = 1
            rv9(i, rc_off + j) = 0
            rvt1(rc_off + j, i) = 1
            rvt9(rc_off + j, i) = 0
          else if (vote == 6) then
            rv1(i, rc_off + j) = 0
            rv9(i, rc_off + j) = 0
            rvt1(rc_off + j, i) = 0
            rvt9(rc_off + j, i) = 0
          else
            ! Missing (9 or anything else)
            rv1(i, rc_off + j) = 0
            rv9(i, rc_off + j) = 1
            rvt1(rc_off + j, i) = 0
            rvt9(rc_off + j, i) = 1
          endif

          start_pos = start_pos + comma_pos
          if (comma_pos == 0) exit
        enddo

        ! Set congress for this legislator (use first period with votes)
        if (p == 1) ncong(i) = p
        ! Check if legislator has any votes in this period
        do j = 1, nrc_period
          if (rv9(i, rc_off + j) == 0) then
            ncong(i) = p  ! Update to latest period with votes
            exit
          endif
        enddo
      enddo
      close(u)

      ! Set congress assignments for roll calls
      do j = 1, nrc_period
        icong(rc_off + j) = p
      enddo

      ! Congress metadata: [numLegislators, numRollCalls, numLegislators]
      ! Must be total legislator count, not just active ones — the Fortran
      ! code uses MCONG(p,3) to size the RCVOTET initialization loop, and
      ! MCONG(p,1) for the RCVOTE loop. Both must cover all rows so the
      ! transpose arrays stay consistent. Missing data is handled internally
      ! via the RCVOTE9/RCVOTET9 boolean arrays.
      mcong(p, 1) = nlegs
      mcong(p, 2) = nrc_period
      mcong(p, 3) = nlegs

      rc_off = rc_off + nrc_period
    enddo

    ! Read W-NOMINATE starting coordinates AFTER id1 is populated from vote data
    write(fn, '(A,A)') trim(dir), '/wnominate_coordinates.csv'
    call load_wnominate_coords(fn, nlegs, ndim, id1, xdata)

    ! Fallback coordinates for legislators without W-NOMINATE starts
    do i = 1, nlegs
      if (abs(xdata(i, 1)) < 1.0d-10 .and. abs(xdata(i, 2)) < 1.0d-10) then
        frac = dble(i) / dble(nlegs)
        xdata(i, 1) = frac - 0.5d0
        xdata(i, 2) = merge(0.1d0, -0.1d0, mod(i,2)==0) * frac
      endif
    enddo

  end subroutine

  subroutine load_wnominate_coords(fname, nlegs, ndim, id1, xdata)
    character(len=*), intent(in) :: fname
    integer, intent(in) :: nlegs, ndim
    integer, intent(inout) :: id1(nlegs)
    double precision, intent(inout) :: xdata(nlegs, ndim)

    character(len=512) :: line
    integer :: u, ios, leg_id, i
    double precision :: c1, c2
    logical :: file_exists

    inquire(file=trim(fname), exist=file_exists)
    if (.not. file_exists) then
      write(*,*) '  WARNING: No W-NOMINATE coordinates file'
      return
    endif

    u = 99
    open(unit=u, file=trim(fname), status='old', action='read', iostat=ios)
    if (ios /= 0) return

    ! Skip header
    read(u, '(A)') line

    do
      read(u, *, iostat=ios) c1, c2, leg_id
      if (ios /= 0) exit

      ! Find this legislator in the id1 array
      do i = 1, nlegs
        if (id1(i) == leg_id) then
          xdata(i, 1) = c1
          if (ndim >= 2) xdata(i, 2) = c2
          exit
        endif
      enddo
    enddo
    close(u)
    write(*,*) '  Loaded W-NOMINATE starting coordinates'
  end subroutine

  subroutine export_results(dir, nlegs, nrcs, ndim, nper, &
                            xdata, zmid, dyn, weights, id1, ncong, niter)
    character(len=*), intent(in) :: dir
    integer, intent(in) :: nlegs, nrcs, ndim, nper, niter
    double precision, intent(in) :: xdata(nlegs, ndim)
    double precision, intent(in) :: zmid(nrcs, ndim), dyn(nrcs, ndim)
    double precision, intent(in) :: weights(ndim + 1)
    integer, intent(in) :: id1(nlegs), ncong(nlegs)

    character(len=512) :: fn
    integer :: u, i

    ! Export coordinates
    write(fn, '(A,A)') trim(dir), '/coordinates.csv'
    u = 50
    open(unit=u, file=trim(fn), status='replace', action='write')
    write(u, '(A)') 'legislator_id,period,coord1D,coord2D'
    do i = 1, nlegs
      ! Only export legislators with non-zero coordinates
      if (abs(xdata(i,1)) > 1.0d-10 .or. abs(xdata(i,2)) > 1.0d-10) then
        write(u, '(I0,A,I0,A,F18.15,A,F18.15)') &
          id1(i), ',', ncong(i), ',', xdata(i,1), ',', xdata(i,2)
      endif
    enddo
    close(u)
    write(*,*) '  Wrote ', trim(fn)

    ! Export bill parameters
    write(fn, '(A,A)') trim(dir), '/bill_parameters.csv'
    open(unit=u, file=trim(fn), status='replace', action='write')
    write(u, '(A)') 'rollcall_id,midpoint1D,midpoint2D,spread1D,spread2D'
    do i = 1, nrcs
      write(u, '(I0,A,F18.15,A,F18.15,A,F18.15,A,F18.15)') &
        i-1, ',', zmid(i,1), ',', zmid(i,2), ',', dyn(i,1), ',', dyn(i,2)
    enddo
    close(u)
    write(*,*) '  Wrote ', trim(fn)

    ! Export summary
    write(fn, '(A,A)') trim(dir), '/summary.csv'
    open(unit=u, file=trim(fn), status='replace', action='write')
    write(u, '(A)') 'parameter,value'
    write(u, '(A,F12.6)') 'w1,', weights(1)
    write(u, '(A,F12.6)') 'w2,', weights(2)
    write(u, '(A,F12.6)') 'beta,', weights(ndim+1)
    write(u, '(A,I0)') 'iterations,', niter
    write(u, '(A,I0)') 'temporal_model,', 0
    write(u, '(A,I0)') 'dimensions,', ndim
    write(u, '(A,I0)') 'periods,', nper
    close(u)
    write(*,*) '  Wrote ', trim(fn)
  end subroutine

end program dwnominate_standalone
